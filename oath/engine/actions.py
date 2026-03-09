"""Action execution for Oath simulator.

Each action function takes a GameState and player index, validates legality,
and returns the modified GameState.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

from oath.enums import (
    ActionType, Phase, Role, Region, CompoundStateType,
    Suit, MAX_CARDS_PER_SITE, MAX_ADVISERS, MAX_SITES,
    CardRestriction, SUIT_CLOCKWISE_ORDER, NUM_SUITS,
)
from oath.state.game_state import GameState, CompoundState, ActionRecord
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.cards.database import get_card, GRAND_SCEPTER_ID
from oath.cards.effects import (
    get_action_effects, get_modifier_effects, get_when_played_effects,
)
from oath.enums import ModifierType
from oath.engine.campaign import recalculate_oathkeeper


class IllegalActionError(Exception):
    """Raised when an action violates game rules."""
    pass


# ── Travel ──────────────────────────────────────────────────────────

def travel_cost(gs: GameState, player_index: int, target_site: int) -> int:
    """Calculate supply cost to travel to target site."""
    player = gs.players[player_index]
    current_site = gs.sites[player.pawn_site]
    target = gs.sites[target_site]

    if player.pawn_site == target_site:
        return 0  # Already there

    # Base cost: 1 per region boundary crossed
    cost = abs(int(current_site.region) - int(target.region))
    if cost == 0:
        cost = 1  # Same region but different site still costs 1

    # Check for travel modifiers from advisers
    gs._modifier_int = cost
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None and player.adviser_faceup[slot]:
            for effect in get_modifier_effects(card_id, ModifierType.TRAVEL):
                if effect.condition(gs, player_index):
                    gs = effect.execute(gs, player_index)
    cost = gs._modifier_int
    gs._modifier_int = 0

    return max(0, cost)


def can_travel(gs: GameState, player_index: int, target_site: int) -> bool:
    """Check if player can legally travel to target site."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    if target_site < 0 or target_site >= MAX_SITES:
        return False

    player = gs.players[player_index]
    if player.pawn_site == target_site:
        return False

    site = gs.sites[target_site]
    if not site.is_faceup and site.site_id == 0:
        return False  # Padding site

    cost = travel_cost(gs, player_index, target_site)
    return player.supply >= cost


def execute_travel(gs: GameState, player_index: int, target_site: int) -> GameState:
    """Execute a Travel action."""
    if not can_travel(gs, player_index, target_site):
        raise IllegalActionError(f"Player {player_index} cannot travel to site {target_site}")

    player = gs.players[player_index]
    cost = travel_cost(gs, player_index, target_site)

    player.supply -= cost
    gs.supply_spent_this_turn += cost

    # Reveal site if facedown
    site = gs.sites[target_site]
    if not site.is_faceup:
        _reveal_site(gs, target_site)

    player.pawn_site = target_site
    gs.actions_taken_this_turn += 1

    _record_action(gs, player_index, ActionType.TRAVEL, target_site=target_site)
    return gs


def _reveal_site(gs: GameState, site_index: int) -> None:
    """Reveal a facedown site, placing favor/secrets and dealing cards."""
    site = gs.sites[site_index]
    site.is_faceup = True

    card_data = get_card(site.site_id)
    site.site_favor = card_data.starting_favor
    site.site_secrets = card_data.starting_secrets

    # Deal cards from world deck to fill site
    for slot in range(site.capacity):
        if site.cards[slot] is None and gs.world_deck:
            card_id = gs.world_deck.pop(0)
            drawn_card = get_card(card_id)
            if drawn_card.is_vision:
                gs.visions_drawn += 1
                next_region = (int(site.region) + 1) % 3
                gs.discard_piles[next_region].append(card_id)
                if gs.world_deck:
                    site.cards[slot] = gs.world_deck.pop(0)
            else:
                site.cards[slot] = card_id

    # Place a relic if available
    if gs.relic_deck:
        site.relics.append(gs.relic_deck.pop(0))


# ── Muster ──────────────────────────────────────────────────────────

def can_muster(gs: GameState, player_index: int, card_slot: int) -> bool:
    """Check if player can muster warbands on a card at their site."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 1:
        return False

    site = gs.sites[player.pawn_site]
    if card_slot >= site.capacity or site.cards[card_slot] is None:
        return False

    card_id = site.cards[card_slot]
    card_data = get_card(card_id)

    # Cannot muster on relics or ruins (§5.2)
    if card_data.is_relic:
        return False
    if card_data.is_edifice and not card_data.suit:
        return False

    # Card must have no favor and no secrets on it (§5.2)
    if site.card_favor[card_slot] != 0 or site.card_secrets[card_slot] != 0:
        return False

    # Must match a suit in the player's advisers or be at ruled site
    # Imperial players (Chancellor + Citizens) share rule over Imperial sites
    if _player_rules_site(gs, player_index, site):
        return True

    # Check if player has matching suit adviser
    if card_data.suit is not None:
        for slot in range(MAX_ADVISERS):
            adv = player.advisers[slot]
            if adv is not None:
                adv_data = get_card(adv)
                if adv_data.suit == card_data.suit:
                    return True

    return False


def execute_muster(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Execute a Muster action: place warbands at player's site."""
    if not can_muster(gs, player_index, card_slot):
        raise IllegalActionError(f"Player {player_index} cannot muster on slot {card_slot}")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    # Place warbands from bank onto site
    warbands_to_place = min(player.warbands_bank, 2)  # Muster places up to 2
    player.warbands_bank -= warbands_to_place
    player.warbands_board += warbands_to_place

    site = gs.sites[player.pawn_site]
    site.warbands += warbands_to_place

    # Set warband color: Imperial (0) for Chancellor/Citizen, player index for Exile
    if gs.is_imperial(player_index):
        site.warband_color = 0
    else:
        site.warband_color = player_index

    # If enough warbands, can rule the site
    _check_rule_site(gs, player_index, player.pawn_site)

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.MUSTER, target_site=player.pawn_site)
    return gs


# ── Trade Favor ─────────────────────────────────────────────────────

def can_trade_favor(gs: GameState, player_index: int, card_slot: int) -> bool:
    """Check if player can trade for favor on a card at their site."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 1:
        return False
    if player.secrets < 1:
        return False

    site = gs.sites[player.pawn_site]
    if card_slot >= site.capacity or site.cards[card_slot] is None:
        return False

    card_id = site.cards[card_slot]
    card_data = get_card(card_id)
    if card_data.suit is None:
        return False

    # Cannot trade with relics or ruins (§2.9)
    if card_data.is_relic:
        return False
    if card_data.is_edifice and not card_data.suit:
        return False

    # Card must have no favor and no secrets on it (§5.3)
    if site.card_favor[card_slot] != 0 or site.card_secrets[card_slot] != 0:
        return False

    # Must have favor available in that suit's bank
    return gs.favor_banks[int(card_data.suit)] > 0


def execute_trade_favor(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Execute Trade Favor: spend secret, place on card, gain favor from bank."""
    if not can_trade_favor(gs, player_index, card_slot):
        raise IllegalActionError(f"Player {player_index} cannot trade favor on slot {card_slot}")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    card_id = site.cards[card_slot]
    card_data = get_card(card_id)

    player.supply -= 1
    gs.supply_spent_this_turn += 1

    # Spend a secret (place on card)
    player.secrets -= 1
    site.card_secrets[card_slot] += 1

    # Gain favor from the card's suit bank: 1 base + 1 per matching faceup adviser
    suit_idx = int(card_data.suit)
    matching_advisers = 0
    for adv_slot in range(MAX_ADVISERS):
        adv_id = player.advisers[adv_slot]
        if adv_id is not None and player.adviser_faceup[adv_slot]:
            adv_data = get_card(adv_id)
            if adv_data.suit == card_data.suit:
                matching_advisers += 1
    favor_gained = min(gs.favor_banks[suit_idx], 1 + matching_advisers)
    gs.favor_banks[suit_idx] -= favor_gained
    player.favor += favor_gained

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.TRADE_FAVOR, target_site=player.pawn_site)
    return gs


# ── Trade Secrets ───────────────────────────────────────────────────

def can_trade_secrets(gs: GameState, player_index: int, card_slot: int) -> bool:
    """Check if player can trade for secrets on a card at their site."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 1:
        return False
    if player.favor < 2:
        return False

    site = gs.sites[player.pawn_site]
    if card_slot >= site.capacity or site.cards[card_slot] is None:
        return False

    card_id = site.cards[card_slot]
    card_data = get_card(card_id)
    if card_data.suit is None:
        return False

    # Cannot trade with relics or ruins (§2.9)
    if card_data.is_relic:
        return False
    if card_data.is_edifice and not card_data.suit:
        return False

    # Card must have no favor and no secrets on it (§5.3)
    if site.card_favor[card_slot] != 0 or site.card_secrets[card_slot] != 0:
        return False

    # Can trade even if you'd get 0 secrets (no matching advisers)
    return True


def execute_trade_secrets(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Execute Trade Secrets: spend favor, place on card, gain secret."""
    if not can_trade_secrets(gs, player_index, card_slot):
        raise IllegalActionError(f"Player {player_index} cannot trade secrets on slot {card_slot}")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    card_id = site.cards[card_slot]
    card_data = get_card(card_id)

    player.supply -= 1
    gs.supply_spent_this_turn += 1

    # Spend 2 favor (place on card)
    player.favor -= 2
    site.card_favor[card_slot] += 2

    # Gain 1 secret per matching faceup adviser (can be 0)
    matching_advisers = 0
    for adv_slot in range(MAX_ADVISERS):
        adv_id = player.advisers[adv_slot]
        if adv_id is not None and player.adviser_faceup[adv_slot]:
            adv_data = get_card(adv_id)
            if adv_data.suit == card_data.suit:
                matching_advisers += 1
    secrets_gained = min(gs.shared_secrets, matching_advisers)
    gs.shared_secrets -= secrets_gained
    player.secrets += secrets_gained

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.TRADE_SECRETS, target_site=player.pawn_site)
    return gs


# ── Search ──────────────────────────────────────────────────────────

def search_cost(gs: GameState, player_index: int | None = None) -> int:
    """Current cost to search (increases as visions are drawn).

    If player_index is provided and that player holds the Darkest Secret,
    the cost is reduced by 1 (minimum 2).
    """
    if gs.visions_drawn <= 1:
        base = 2
    elif gs.visions_drawn <= 3:
        base = 3
    else:
        base = 4

    # Darkest Secret holder power: reduce search cost by 1 (minimum 2)
    if player_index is not None and gs.darkest_secret_holder == player_index:
        base = max(2, base - 1)

    return base


def can_search_deck(gs: GameState, player_index: int) -> bool:
    """Check if player can search from the world deck."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    return player.supply >= search_cost(gs, player_index) and len(gs.world_deck) > 0


def can_search_discard(gs: GameState, player_index: int) -> bool:
    """Check if player can search from a discard pile."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    region_idx = int(site.region)
    return (player.supply >= search_cost(gs, player_index) and
            len(gs.discard_piles[region_idx]) > 0)


def execute_search(gs: GameState, player_index: int, source: str) -> GameState:
    """Begin a Search action. Draws cards and enters compound state."""
    player = gs.players[player_index]
    cost = search_cost(gs, player_index)

    if source == "deck":
        if not can_search_deck(gs, player_index):
            raise IllegalActionError("Cannot search deck")
    else:
        if not can_search_discard(gs, player_index):
            raise IllegalActionError("Cannot search discard")

    player.supply -= cost
    gs.supply_spent_this_turn += cost

    # Draw cards
    drawn: list[int] = []
    if source == "deck":
        for _ in range(3):
            if not gs.world_deck:
                break
            card_id = gs.world_deck.pop(0)
            card_data = get_card(card_id)
            if card_data.is_vision:
                gs.visions_drawn += 1
                # Vision goes to player as a potential reveal
                drawn.append(card_id)
                break  # Stop drawing on vision
            drawn.append(card_id)
    else:
        site = gs.sites[player.pawn_site]
        region_idx = int(site.region)
        pile = gs.discard_piles[region_idx]
        for _ in range(3):
            if not pile:
                break
            drawn.append(pile.pop())

    if not drawn:
        gs.actions_taken_this_turn += 1
        _record_action(gs, player_index, ActionType.SEARCH)
        return gs

    # Enter compound state
    gs.compound_state = CompoundState(
        state_type=CompoundStateType.SEARCH_CHOOSE,
        drawn_cards=drawn,
        search_source=source,
        cards_remaining=[True] * len(drawn),
    )

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.SEARCH)
    return gs


def execute_search_play(
    gs: GameState, player_index: int,
    card_index: int, destination: str,
) -> GameState:
    """Play a drawn card from search to site or advisers."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.SEARCH_CHOOSE:
        raise IllegalActionError("Not in search choose state")

    if card_index >= len(cs.drawn_cards) or not cs.cards_remaining[card_index]:
        raise IllegalActionError(f"Card index {card_index} not available")

    card_id = cs.drawn_cards[card_index]
    card_data = get_card(card_id)
    player = gs.players[player_index]

    if card_data.is_vision:
        if card_id == 225:
            # Conspiracy (§5.1.4.IV): auto-resolve simplified effect, then return to box
            _resolve_conspiracy(gs, player_index)
            cs.cards_remaining[card_index] = False
            _finish_search_if_done(gs, player_index)
            return gs
        # Regular visions go to player's revealed vision slot
        player.revealed_vision = card_id
        cs.cards_remaining[card_index] = False
        _finish_search_if_done(gs, player_index)
        return gs

    if destination == "site":
        if card_data.restriction == CardRestriction.ADVISER_ONLY:
            raise IllegalActionError("Card is adviser-only")
        site = gs.sites[player.pawn_site]
        slot = site.first_empty_card_slot()
        if slot is None:
            # People's Favor holder power: auto-discard first card to make room
            if gs.peoples_favor_holder == player_index:
                _pf_auto_discard(gs, site)
                slot = site.first_empty_card_slot()
            if slot is None:
                raise IllegalActionError("No empty card slot at site")
        site.cards[slot] = card_id
    elif destination in ("adviser_up", "adviser_down"):
        if card_data.restriction == CardRestriction.SITE_ONLY:
            raise IllegalActionError("Card is site-only")
        slot = player.first_empty_adviser_slot()
        if slot is None:
            # Must replace an existing non-LOCKED adviser
            slot = None
            for s in range(MAX_ADVISERS):
                if player.advisers[s] is not None:
                    adv_data = get_card(player.advisers[s])
                    if adv_data.restriction != CardRestriction.LOCKED:
                        slot = s
                        break
            if slot is None:
                raise IllegalActionError("All adviser slots are locked")
            old_card = player.advisers[slot]
            if old_card is not None:
                site = gs.sites[player.pawn_site]
                next_region = (int(site.region) + 1) % 3
                gs.discard_piles[next_region].append(old_card)
        player.advisers[slot] = card_id
        player.adviser_faceup[slot] = (destination == "adviser_up")
    else:
        raise IllegalActionError(f"Invalid destination: {destination}")

    # Trigger WHEN_PLAYED effects
    for effect in get_when_played_effects(card_id):
        if effect.condition(gs, player_index):
            gs = effect.execute(gs, player_index)

    cs.cards_remaining[card_index] = False
    _finish_search_if_done(gs, player_index)
    return gs


def execute_search_discard(gs: GameState, player_index: int, card_index: int) -> GameState:
    """Discard a drawn card from search."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.SEARCH_CHOOSE:
        raise IllegalActionError("Not in search choose state")

    if card_index >= len(cs.drawn_cards) or not cs.cards_remaining[card_index]:
        raise IllegalActionError(f"Card index {card_index} not available")

    card_id = cs.drawn_cards[card_index]
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    next_region = (int(site.region) + 1) % 3
    gs.discard_piles[next_region].append(card_id)

    cs.cards_remaining[card_index] = False
    _finish_search_if_done(gs, player_index)
    return gs


def _resolve_conspiracy(gs: GameState, player_index: int) -> None:
    """Resolve Conspiracy vision (card 225) simplified auto-resolution (§5.1.4.IV).

    Checks if any player at the same site has relics/banners the player could take.
    Requires >=2 advisers matching ANY of target's adviser suits and >=1 secret.
    Takes the most valuable relic/banner, burns resources, then removes card from game.
    """
    player = gs.players[player_index]

    # Must have at least 1 secret to spend
    if player.secrets < 1:
        return  # Card is still removed from game (handled by caller)

    # Get player's adviser suits (only faceup advisers count)
    player_adviser_suits: dict[int, int] = {}  # suit -> count
    for slot in range(MAX_ADVISERS):
        if player.advisers[slot] is not None and player.adviser_faceup[slot]:
            adv_data = get_card(player.advisers[slot])
            if adv_data.suit is not None:
                player_adviser_suits[int(adv_data.suit)] = (
                    player_adviser_suits.get(int(adv_data.suit), 0) + 1
                )

    best_target = None
    best_item = None  # ("relic", relic_idx) or ("pf",) or ("ds",)
    best_value = -1

    for ti in range(gs.num_players):
        if ti == player_index:
            continue
        target = gs.players[ti]
        if target.pawn_site != player.pawn_site:
            continue

        # Check suit match: player needs >=2 advisers matching ANY of target's adviser suits
        target_suits = set()
        for slot in range(MAX_ADVISERS):
            if target.advisers[slot] is not None:
                t_data = get_card(target.advisers[slot])
                if t_data.suit is not None:
                    target_suits.add(int(t_data.suit))

        has_match = False
        for suit_val in target_suits:
            if player_adviser_suits.get(suit_val, 0) >= 2:
                has_match = True
                break

        if not has_match:
            continue

        # Evaluate relics (value 3 each, arbitrary)
        for ri, relic_id in enumerate(target.relics):
            value = 3
            if value > best_value:
                best_value = value
                best_target = ti
                best_item = ("relic", ri)

        # Evaluate banners (People's Favor = value 5, Darkest Secret = value 4)
        if gs.peoples_favor_holder == ti:
            value = 5
            if value > best_value:
                best_value = value
                best_target = ti
                best_item = ("pf",)

        if gs.darkest_secret_holder == ti:
            value = 4
            if value > best_value:
                best_value = value
                best_target = ti
                best_item = ("ds",)

    if best_target is not None and best_item is not None:
        # Burn 1 secret
        player.secrets -= 1

        if best_item[0] == "relic":
            relic_idx = best_item[1]
            relic_id = gs.players[best_target].relics.pop(relic_idx)
            player.relics.append(relic_id)
        elif best_item[0] == "pf":
            # Take People's Favor
            gs.peoples_favor_holder = player_index
            # Burn 2 favor/secrets from the banner
            burn_remaining = 2
            if gs.peoples_favor_tokens >= burn_remaining:
                gs.peoples_favor_tokens -= burn_remaining
            else:
                burn_remaining -= gs.peoples_favor_tokens
                gs.peoples_favor_tokens = 0
                # Remaining burn from player's favor/secrets (simplified)
            # Flip PF if taken (§2.5.3)
            gs.peoples_favor_is_mob = not gs.peoples_favor_is_mob
            recalculate_oathkeeper(gs)
        elif best_item[0] == "ds":
            # Take Darkest Secret
            gs.darkest_secret_holder = player_index
            # Burn 2 favor/secrets from the banner
            burn_remaining = 2
            if gs.darkest_secret_tokens >= burn_remaining:
                gs.darkest_secret_tokens -= burn_remaining
            else:
                burn_remaining -= gs.darkest_secret_tokens
                gs.darkest_secret_tokens = 0
            recalculate_oathkeeper(gs)

    # Conspiracy is returned to the box (not discarded, not added anywhere)
    # The caller already marks cards_remaining[card_index] = False
    # and does NOT place it as an adviser or on a site.


def _finish_search_if_done(gs: GameState, player_index: int) -> None:
    """Check if all drawn cards have been handled, and exit compound state."""
    cs = gs.compound_state
    if cs is None:
        return

    remaining = sum(1 for r in cs.cards_remaining if r)
    if remaining == 0:
        gs.compound_state = None


# ── Recover ─────────────────────────────────────────────────────────

def can_recover_relic(gs: GameState, player_index: int, relic_slot: int) -> bool:
    """Check if player can recover a relic at their site."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.supply < 1:
        return False

    site = gs.sites[player.pawn_site]
    if not _player_rules_site(gs, player_index, site):
        return False

    return relic_slot < len(site.relics)


def execute_recover_relic(gs: GameState, player_index: int, relic_slot: int) -> GameState:
    """Recover a relic from the current site."""
    if not can_recover_relic(gs, player_index, relic_slot):
        raise IllegalActionError(f"Cannot recover relic slot {relic_slot}")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    player.supply -= 1
    gs.supply_spent_this_turn += 1

    relic_id = site.relics.pop(relic_slot)
    player.relics.append(relic_id)

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.RECOVER, target_site=player.pawn_site)
    return gs


def can_recover_peoples_favor(gs: GameState, player_index: int) -> bool:
    """Check if player can recover the People's Favor (§5.4.4).

    Player must pay favor > current peoples_favor_tokens (minimum cost =
    tokens + 1).  Must also have highest favor among all players.
    """
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.supply < 1:
        return False
    if gs.peoples_favor_holder is not None:
        return False

    # Must be able to pay cost exceeding current banner tokens
    cost = gs.peoples_favor_tokens + 1
    if player.favor < cost:
        return False

    # Must have most favor among all players (after paying cost)
    # Check pre-payment: must currently have highest favor
    max_favor = max(p.favor for p in gs.players)
    return player.favor >= max_favor and player.favor > 0


def execute_recover_peoples_favor(gs: GameState, player_index: int) -> GameState:
    """Recover the People's Favor banner (§5.4.4).

    1. Pay cost = peoples_favor_tokens + 1 (minimum to exceed current value).
       The cost favor is placed ON the banner as new tokens.
    2. The OLD tokens that were on the banner get distributed to favor banks
       one-by-one starting from suit 0, wrapping clockwise.
    3. Flip to non-Mob side if on Mob side.
    4. Transfer ownership.
    """
    if not can_recover_peoples_favor(gs, player_index):
        raise IllegalActionError("Cannot recover People's Favor")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    # Step 1: Pay favor cost (minimum amount exceeding current banner value)
    old_tokens = gs.peoples_favor_tokens
    cost = old_tokens + 1
    player.favor -= cost

    # The cost paid becomes the new token count on the banner
    gs.peoples_favor_tokens = cost

    # Step 2: Distribute old tokens to favor banks clockwise starting from suit 0
    suit_idx = 0
    for _ in range(old_tokens):
        bank_index = int(SUIT_CLOCKWISE_ORDER[suit_idx])
        gs.favor_banks[bank_index] += 1
        suit_idx = (suit_idx + 1) % NUM_SUITS

    # Step 3: Flip to non-Mob side
    gs.peoples_favor_is_mob = False

    # Step 4: Transfer ownership
    gs.peoples_favor_holder = player_index
    recalculate_oathkeeper(gs)

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.RECOVER_PEOPLES_FAVOR)
    return gs


def can_recover_darkest_secret(gs: GameState, player_index: int) -> bool:
    """Check if player can recover the Darkest Secret (§5.4.1).

    When the DS is unclaimed, standard recovery rules apply (most secrets).
    When recovering from another player:
    - Always allowed if recovering from yourself.
    - Requires that at least one card at the holder's site has a suit that
      does NOT match any of the holder's faceup adviser suits.
    - Cannot recover if the holder has no faceup advisers (no suits to compare).
    """
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.supply < 1:
        return False

    holder = gs.darkest_secret_holder

    if holder is not None:
        # DS is held by someone
        if holder == player_index:
            # Recovering from yourself is always allowed
            return True

        # Check §5.4.1 restriction: holder must have faceup advisers
        holder_player = gs.players[holder]
        holder_suits = set()
        for slot in range(MAX_ADVISERS):
            adv_id = holder_player.advisers[slot]
            if adv_id is not None and holder_player.adviser_faceup[slot]:
                adv_data = get_card(adv_id)
                if adv_data.suit is not None:
                    holder_suits.add(adv_data.suit)

        if not holder_suits:
            # Holder has no faceup advisers with suits; cannot recover
            return False

        # Check if any card at the holder's site has a suit NOT in holder's adviser suits
        holder_site = gs.sites[holder_player.pawn_site]
        has_unmatched_card = False
        for slot in range(holder_site.capacity):
            card_id = holder_site.cards[slot]
            if card_id is not None:
                card_data = get_card(card_id)
                if card_data.suit is not None and card_data.suit not in holder_suits:
                    has_unmatched_card = True
                    break

        if not has_unmatched_card:
            return False

        # Must be able to pay cost exceeding current banner tokens
        cost = gs.darkest_secret_tokens + 1
        if player.secrets < cost:
            return False

        # Must still have most secrets
        max_secrets = max(p.secrets for p in gs.players)
        return player.secrets >= max_secrets and player.secrets > 0
    else:
        # DS is unclaimed, standard recovery
        cost = gs.darkest_secret_tokens + 1
        if player.secrets < cost:
            return False

        max_secrets = max(p.secrets for p in gs.players)
        return player.secrets >= max_secrets and player.secrets > 0


def execute_recover_darkest_secret(gs: GameState, player_index: int) -> GameState:
    """Recover the Darkest Secret banner (§5.4.4).

    1. Pay cost = darkest_secret_tokens + 1 secrets (minimum to exceed).
       The cost is placed ON the banner as new tokens.
    2. Take 1 secret from the OLD banner tokens to your board.
    3. Give the REST of the old tokens to the previous holder.
       Special: if recovering from yourself, take ALL old secrets instead.
    4. Transfer ownership.
    """
    if not can_recover_darkest_secret(gs, player_index):
        raise IllegalActionError("Cannot recover Darkest Secret")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    old_holder = gs.darkest_secret_holder
    old_tokens = gs.darkest_secret_tokens

    # Step 1: Pay secret cost (minimum amount exceeding current banner value)
    cost = old_tokens + 1
    player.secrets -= cost

    # The cost paid becomes the new token count on the banner
    gs.darkest_secret_tokens = cost

    # Steps 2-3: Distribute old tokens
    if old_tokens > 0:
        if old_holder == player_index or old_holder is None:
            # Recovering from yourself (or unclaimed): take ALL old secrets
            player.secrets += old_tokens
        else:
            # Take 1 secret from old tokens to your board
            player.secrets += 1
            # Give the rest to the previous holder
            remaining = old_tokens - 1
            if remaining > 0:
                gs.players[old_holder].secrets += remaining

    # Step 4: Transfer ownership
    gs.darkest_secret_holder = player_index
    recalculate_oathkeeper(gs)

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.RECOVER_DARKEST_SECRET)
    return gs


# ── Minor Actions ───────────────────────────────────────────────────

def can_flip_adviser(gs: GameState, player_index: int, slot: int) -> bool:
    """Check if player can flip a facedown adviser faceup."""
    if gs.phase != Phase.ACT:
        return False
    player = gs.players[player_index]
    return (slot < MAX_ADVISERS and
            player.advisers[slot] is not None and
            not player.adviser_faceup[slot])


def execute_flip_adviser(gs: GameState, player_index: int, slot: int) -> GameState:
    """Flip a facedown adviser to faceup (minor action, free)."""
    if not can_flip_adviser(gs, player_index, slot):
        raise IllegalActionError(f"Cannot flip adviser slot {slot}")

    gs.players[player_index].adviser_faceup[slot] = True
    _record_action(gs, player_index, ActionType.MINOR_FLIP_ADVISER)
    return gs


def can_move_warbands_to_board(gs: GameState, player_index: int) -> bool:
    """Check if player can move warbands from their site to their board (§6.5).

    Requirements:
    - Must be in ACT phase
    - Player must rule their current site
    - Must have more than 1 warband at the site (keep at least 1 to maintain rule)
    """
    if gs.phase != Phase.ACT:
        return False
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    if not _player_rules_site(gs, player_index, site):
        return False
    # Must have more than 1 warband at site to move any
    return site.warbands > 1


def execute_move_warbands_to_board(gs: GameState, player_index: int) -> GameState:
    """Move all warbands except 1 from site to board (§6.5).

    Moves warbands_at_site - 1 warbands to the player's bank.
    Keeps 1 warband on the site to maintain rule.
    """
    if not can_move_warbands_to_board(gs, player_index):
        raise IllegalActionError(f"Player {player_index} cannot move warbands to board")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    # Move all except 1 from site to bank
    moving = site.warbands - 1
    site.warbands -= moving
    player.warbands_board -= moving
    player.warbands_bank += moving

    _record_action(gs, player_index, ActionType.MINOR_WARBANDS, target_site=player.pawn_site)
    return gs


def can_move_warbands_to_site(gs: GameState, player_index: int) -> bool:
    """Check if player can move warbands from board to site (§6.5).

    Requirements:
    - Must be in ACT phase
    - Player must rule their current site
    - Must have warbands in bank to move
    """
    if gs.phase != Phase.ACT:
        return False
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    if not _player_rules_site(gs, player_index, site):
        return False
    return player.warbands_bank > 0


def execute_move_warbands_to_site(gs: GameState, player_index: int) -> GameState:
    """Move all bank warbands to site (§6.5).

    Moves all warbands from the player's bank to the site.
    """
    if not can_move_warbands_to_site(gs, player_index):
        raise IllegalActionError(f"Player {player_index} cannot move warbands to site")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    moving = player.warbands_bank
    player.warbands_bank -= moving
    player.warbands_board += moving
    site.warbands += moving

    _record_action(gs, player_index, ActionType.MINOR_WARBANDS, target_site=player.pawn_site)
    return gs


def can_use_card_action(gs: GameState, player_index: int, card_source: int) -> bool:
    """Check if player can use a card's action ability.
    card_source: 0-2 = adviser slots, 3-5 = site card slots.
    """
    if gs.phase != Phase.ACT:
        return False
    player = gs.players[player_index]

    if card_source < 3:
        # Adviser
        card_id = player.advisers[card_source]
        if card_id is None or not player.adviser_faceup[card_source]:
            return False
    else:
        # Site card
        site = gs.sites[player.pawn_site]
        slot = card_source - 3
        if slot >= site.capacity or site.cards[slot] is None:
            return False
        card_id = site.cards[slot]

    effects = get_action_effects(card_id)
    if not effects:
        return False

    return any(e.condition(gs, player_index) for e in effects)


def execute_use_card_action(gs: GameState, player_index: int, card_source: int) -> GameState:
    """Use a card's action ability."""
    if not can_use_card_action(gs, player_index, card_source):
        raise IllegalActionError(f"Cannot use card action from source {card_source}")

    player = gs.players[player_index]

    if card_source < 3:
        card_id = player.advisers[card_source]
    else:
        site = gs.sites[player.pawn_site]
        slot = card_source - 3
        card_id = site.cards[slot]

    effects = get_action_effects(card_id)
    for effect in effects:
        if effect.condition(gs, player_index):
            # Pay costs
            player.secrets -= effect.cost_secrets
            player.favor -= effect.cost_favor
            gs.shared_secrets += effect.cost_burn_secrets
            # Execute
            gs = effect.execute(gs, player_index)
            break

    _record_action(gs, player_index, ActionType.MINOR_USE_ACTION)
    return gs


# ── Citizenship ─────────────────────────────────────────────────────

def can_offer_citizenship(gs: GameState, player_index: int, target: int) -> bool:
    """Check if Chancellor can offer citizenship to an exile."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.role != Role.CHANCELLOR:
        return False
    if target <= 0 or target >= gs.num_players:
        return False
    target_player = gs.players[target]
    return target_player.role == Role.EXILE


def execute_offer_citizenship(gs: GameState, player_index: int, target: int) -> GameState:
    """Chancellor offers citizenship to an exile."""
    if not can_offer_citizenship(gs, player_index, target):
        raise IllegalActionError(f"Cannot offer citizenship to player {target}")

    gs.pending_citizenship_target = target
    gs.compound_state = CompoundState(
        state_type=CompoundStateType.RELIQUARY_CHOOSE,
        citizenship_offerer=player_index,
        citizenship_target=target,
    )

    _record_action(gs, player_index, ActionType.OFFER_CITIZENSHIP, target_player=target)
    return gs


def execute_reliquary_choose(gs: GameState, player_index: int, slot: int) -> GameState:
    """Chancellor chooses reliquary slot for citizenship offer."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.RELIQUARY_CHOOSE:
        raise IllegalActionError("Not in reliquary choose state")

    cs.reliquary_slot = slot
    cs.state_type = CompoundStateType.CITIZENSHIP_RESPONSE
    return gs


def execute_accept_citizenship(gs: GameState, player_index: int) -> GameState:
    """Exile accepts citizenship offer."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CITIZENSHIP_RESPONSE:
        raise IllegalActionError("Not in citizenship response state")
    if cs.citizenship_target != player_index:
        raise IllegalActionError(
            f"Player {player_index} is not the citizenship target (target={cs.citizenship_target})"
        )

    player = gs.players[player_index]
    player.role = Role.CITIZEN

    # Convert this player's warbands at sites to Imperial color (0)
    for site in gs.sites:
        if site.warband_color == player_index and site.warbands > 0:
            site.warband_color = 0
            # Site ruling transfers to Chancellor (Imperial)
            site.ruling_player = gs.chancellor_index

    # Give a relic from reliquary if available
    if cs.reliquary_slot is not None and cs.reliquary_slot < len(gs.reliquary):
        relic = gs.reliquary.pop(cs.reliquary_slot)
        player.relics.append(relic)

    gs.compound_state = None
    gs.pending_citizenship_target = None

    _record_action(gs, player_index, ActionType.ACCEPT_CITIZENSHIP)
    return gs


def execute_decline_citizenship(gs: GameState, player_index: int) -> GameState:
    """Exile declines citizenship offer."""
    cs = gs.compound_state
    if cs is not None and cs.citizenship_target != player_index:
        raise IllegalActionError(
            f"Player {player_index} is not the citizenship target (target={cs.citizenship_target})"
        )
    gs.compound_state = None
    gs.pending_citizenship_target = None
    _record_action(gs, player_index, ActionType.DECLINE_CITIZENSHIP)
    return gs


def _self_exile_cost(gs: GameState, player_index: int) -> int:
    """Calculate the favor cost to self-exile (§6.8).

    Cost = number of secrets on player's board (personal secrets + secrets on
    adviser/denizen/relic/edifice cards) + number of warbands on player's board.
    """
    player = gs.players[player_index]
    # Count secrets on advisers at the player's site cards
    adviser_secrets = 0
    site = gs.sites[player.pawn_site]
    for slot in range(MAX_ADVISERS):
        if player.advisers[slot] is not None:
            # Advisers don't directly hold secrets in this model;
            # the player's personal secrets count covers board secrets
            pass
    cost = player.secrets + player.warbands_board
    return cost


def can_self_exile(gs: GameState, player_index: int) -> bool:
    """Check if a Citizen can legally self-exile (§6.8).

    Requirements:
    - Player must be a Citizen.
    - Player must NOT hold the Grand Scepter.
    - Player must have enough favor to pay the cost.
    """
    player = gs.players[player_index]
    if player.role != Role.CITIZEN:
        return False
    if GRAND_SCEPTER_ID in player.relics:
        return False
    cost = _self_exile_cost(gs, player_index)
    return player.favor >= cost


def execute_self_exile(gs: GameState, player_index: int) -> GameState:
    """Citizen voluntarily self-exiles (§6.8).

    Pays favor equal to (secrets on board + warbands on board) to the
    Grand Scepter holder. Then becomes an Exile.
    """
    if not can_self_exile(gs, player_index):
        raise IllegalActionError("Cannot self-exile: must be Citizen, not hold Grand Scepter, and have enough favor")

    player = gs.players[player_index]
    cost = _self_exile_cost(gs, player_index)

    # Pay favor to Grand Scepter holder
    player.favor -= cost
    # Find Grand Scepter holder and give them the favor
    for i, p in enumerate(gs.players):
        if GRAND_SCEPTER_ID in p.relics:
            p.favor += cost
            break
    else:
        # No Grand Scepter holder; favor goes to supply/bank (lost)
        pass

    player.role = Role.EXILE
    _record_action(gs, player_index, ActionType.SELF_EXILE)
    return gs


# ── Exile a Citizen (§6.7) ─────────────────────────────────────────

def _exile_citizen_cost(gs: GameState, player_index: int, target_index: int) -> int:
    """Calculate favor cost for exiling a citizen (§6.7).

    Base cost is 5, modified by:
    - +1 if target is Oathkeeper, +1 if target holds People's Favor
    - -1 if player is Oathkeeper, -1 if player holds People's Favor
    """
    cost = 5

    # Target modifiers (increase cost)
    if gs.oathkeeper_holder == target_index:
        cost += 1
    if gs.peoples_favor_holder == target_index:
        cost += 1

    # Player modifiers (decrease cost)
    if gs.oathkeeper_holder == player_index:
        cost -= 1
    if gs.peoples_favor_holder == player_index:
        cost -= 1

    return max(0, cost)


def can_exile_citizen(gs: GameState, player_index: int, target_index: int) -> bool:
    """Check if player can exile a citizen (§6.7).

    Requirements:
    - Player holds Grand Scepter
    - Target is a Citizen
    - Player has enough favor to pay
    - Not in compound action
    - ACT phase
    - Target is not self
    """
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    if player_index == target_index:
        return False

    player = gs.players[player_index]
    if GRAND_SCEPTER_ID not in player.relics:
        return False

    target = gs.players[target_index]
    if target.role != Role.CITIZEN:
        return False

    cost = _exile_citizen_cost(gs, player_index, target_index)
    return player.favor >= cost


def execute_exile_citizen(gs: GameState, player_index: int, target_index: int) -> GameState:
    """Execute exile-a-citizen action (§6.7).

    1. Pay favor to target
    2. Target becomes Exile
    3. Target refreshes supply to leftmost position
    """
    if not can_exile_citizen(gs, player_index, target_index):
        raise IllegalActionError(
            f"Player {player_index} cannot exile citizen {target_index}"
        )

    player = gs.players[player_index]
    target = gs.players[target_index]
    cost = _exile_citizen_cost(gs, player_index, target_index)

    # Pay favor to the target
    player.favor -= cost
    target.favor += cost

    # Target becomes Exile
    target.role = Role.EXILE

    # Target refreshes supply (reset to starting exile supply level)
    target.supply = 7

    _record_action(gs, player_index, ActionType.EXILE_CITIZEN, target_player=target_index)
    return gs


# ── End Act Phase ───────────────────────────────────────────────────

def execute_end_act_phase(gs: GameState, player_index: int) -> GameState:
    """Player voluntarily ends their act phase."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        raise IllegalActionError("Cannot end act phase now")

    gs.phase = Phase.REST
    _record_action(gs, player_index, ActionType.END_ACT_PHASE)
    return gs


# ── Helpers ─────────────────────────────────────────────────────────

def _pf_auto_discard(gs: GameState, site: 'SiteState') -> None:
    """People's Favor holder power: auto-discard the first card at a full site.

    Simplified version of §2.5 — discards the first non-None card at the site
    to the next region's discard pile.
    """
    for slot in range(site.capacity):
        if site.cards[slot] is not None:
            card_id = site.cards[slot]
            next_region = (int(site.region) + 1) % 3
            gs.discard_piles[next_region].append(card_id)
            site.cards[slot] = None
            site.card_favor[slot] = 0
            site.card_secrets[slot] = 0
            break


def _player_rules_site(gs: GameState, player_index: int, site: SiteState) -> bool:
    """Check if player rules a site, accounting for Imperial warband sharing."""
    if site.ruling_player == player_index:
        return True
    # Imperial sharing: Chancellor and Citizens share rule over Imperial sites
    if (gs.is_imperial(player_index)
            and site.ruling_player is not None
            and gs.is_imperial(site.ruling_player)
            and site.warband_color == 0
            and site.warbands > 0):
        return True
    return False


def _check_rule_site(gs: GameState, player_index: int, site_index: int) -> None:
    """Check if player now rules the site (most warbands there)."""
    site = gs.sites[site_index]
    if not site.is_faceup:
        return

    # Count warbands per player at this site
    # For simplicity: player who just mustered checks against current ruler
    if site.ruling_player is None:
        site.ruling_player = player_index
        site.warband_color = 0 if gs.is_imperial(player_index) else player_index
        recalculate_oathkeeper(gs)
    elif site.ruling_player != player_index:
        # Would need campaign to take over in full rules
        # For now just track warbands
        pass


def _record_action(
    gs: GameState, player_index: int, action_type: ActionType,
    target_site: Optional[int] = None, target_player: Optional[int] = None,
    was_successful: bool = False,
) -> None:
    """Record an action in the history."""
    logger.debug(
        "P%d %s site=%s target_player=%s",
        player_index, action_type.name, target_site, target_player,
    )
    gs.action_history.append(ActionRecord(
        player_index=player_index,
        action_type=action_type,
        target_site=target_site,
        target_player=target_player,
        was_successful=was_successful,
    ))
    # Keep only last 20 actions
    if len(gs.action_history) > 20:
        gs.action_history = gs.action_history[-20:]

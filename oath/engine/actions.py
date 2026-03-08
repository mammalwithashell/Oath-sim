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
    CardRestriction,
)
from oath.state.game_state import GameState, CompoundState, ActionRecord
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.cards.database import get_card
from oath.cards.effects import (
    get_action_effects, get_modifier_effects, get_when_played_effects,
)
from oath.enums import ModifierType


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
                gs.discard_piles[int(site.region)].append(card_id)
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
    # Must match a suit in the player's advisers or be at ruled site
    # For simplicity: player must rule the site or have matching suit adviser
    if site.ruling_player == player_index:
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

    # Gain favor from the card's suit bank
    suit_idx = int(card_data.suit)
    favor_gained = min(gs.favor_banks[suit_idx], 1)
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
    if player.favor < 1:
        return False

    site = gs.sites[player.pawn_site]
    if card_slot >= site.capacity or site.cards[card_slot] is None:
        return False

    return gs.shared_secrets > 0


def execute_trade_secrets(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Execute Trade Secrets: spend favor, place on card, gain secret."""
    if not can_trade_secrets(gs, player_index, card_slot):
        raise IllegalActionError(f"Player {player_index} cannot trade secrets on slot {card_slot}")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    player.supply -= 1
    gs.supply_spent_this_turn += 1

    # Spend favor (place on card)
    player.favor -= 1
    site.card_favor[card_slot] += 1

    # Gain a secret from shared bank
    secrets_gained = min(gs.shared_secrets, 1)
    gs.shared_secrets -= secrets_gained
    player.secrets += secrets_gained

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.TRADE_SECRETS, target_site=player.pawn_site)
    return gs


# ── Search ──────────────────────────────────────────────────────────

def search_cost(gs: GameState) -> int:
    """Current cost to search (increases as visions are drawn)."""
    if gs.visions_drawn <= 1:
        return 2
    elif gs.visions_drawn <= 3:
        return 3
    else:
        return 4


def can_search_deck(gs: GameState, player_index: int) -> bool:
    """Check if player can search from the world deck."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    return player.supply >= search_cost(gs) and len(gs.world_deck) > 0


def can_search_discard(gs: GameState, player_index: int) -> bool:
    """Check if player can search from a discard pile."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    region_idx = int(site.region)
    return (player.supply >= search_cost(gs) and
            len(gs.discard_piles[region_idx]) > 0)


def execute_search(gs: GameState, player_index: int, source: str) -> GameState:
    """Begin a Search action. Draws cards and enters compound state."""
    player = gs.players[player_index]
    cost = search_cost(gs)

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
        # Visions go to player's revealed vision slot
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
            raise IllegalActionError("No empty card slot at site")
        site.cards[slot] = card_id
    elif destination in ("adviser_up", "adviser_down"):
        if card_data.restriction == CardRestriction.SITE_ONLY:
            raise IllegalActionError("Card is site-only")
        slot = player.first_empty_adviser_slot()
        if slot is None:
            # Must replace an existing adviser
            slot = 0  # Replace first adviser
            old_card = player.advisers[slot]
            if old_card is not None:
                site = gs.sites[player.pawn_site]
                gs.discard_piles[int(site.region)].append(old_card)
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
    gs.discard_piles[int(site.region)].append(card_id)

    cs.cards_remaining[card_index] = False
    _finish_search_if_done(gs, player_index)
    return gs


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
    if site.ruling_player != player_index:
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
    """Check if player can recover the People's Favor."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.supply < 1:
        return False
    if gs.peoples_favor_holder is not None:
        return False

    # Must have most favor in the most populated suit
    # Simplified: must have highest favor among all players
    max_favor = max(p.favor for p in gs.players)
    return player.favor >= max_favor and player.favor > 0


def execute_recover_peoples_favor(gs: GameState, player_index: int) -> GameState:
    """Recover the People's Favor banner."""
    if not can_recover_peoples_favor(gs, player_index):
        raise IllegalActionError("Cannot recover People's Favor")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    gs.peoples_favor_holder = player_index

    gs.actions_taken_this_turn += 1
    _record_action(gs, player_index, ActionType.RECOVER_PEOPLES_FAVOR)
    return gs


def can_recover_darkest_secret(gs: GameState, player_index: int) -> bool:
    """Check if player can recover the Darkest Secret."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False
    player = gs.players[player_index]
    if player.supply < 1:
        return False
    if gs.darkest_secret_holder is not None:
        return False

    # Must have most secrets
    max_secrets = max(p.secrets for p in gs.players)
    return player.secrets >= max_secrets and player.secrets > 0


def execute_recover_darkest_secret(gs: GameState, player_index: int) -> GameState:
    """Recover the Darkest Secret banner."""
    if not can_recover_darkest_secret(gs, player_index):
        raise IllegalActionError("Cannot recover Darkest Secret")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    gs.darkest_secret_holder = player_index

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


def execute_self_exile(gs: GameState, player_index: int) -> GameState:
    """Citizen voluntarily self-exiles."""
    player = gs.players[player_index]
    if player.role != Role.CITIZEN:
        raise IllegalActionError("Only citizens can self-exile")

    player.role = Role.EXILE
    _record_action(gs, player_index, ActionType.SELF_EXILE)
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

def _check_rule_site(gs: GameState, player_index: int, site_index: int) -> None:
    """Check if player now rules the site (most warbands there)."""
    site = gs.sites[site_index]
    if not site.is_faceup:
        return

    # Count warbands per player at this site
    # For simplicity: player who just mustered checks against current ruler
    if site.ruling_player is None:
        site.ruling_player = player_index
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

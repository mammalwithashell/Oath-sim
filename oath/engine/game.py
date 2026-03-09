"""Main game loop and setup for Oath simulator."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

from oath.enums import (
    Role, Region, Phase, OathGoal, SuccessorGoal, TitleSide,
    Suit, MAX_SITES, MAX_WARBANDS_CHANCELLOR, MAX_WARBANDS_EXILE,
    MAX_ROUNDS, MAX_SUPPLY, ActionType, SUIT_CLOCKWISE_ORDER,
)
from oath.state.game_state import GameState, ActionRecord
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.cards.database import (
    get_card, get_first_game_denizen_ids, get_first_game_site_ids,
    get_first_game_relic_ids, get_vision_ids, get_all_denizen_ids,
    RESOURCE_SITE_IDS,
)
from oath.cards.effects import get_wake_effects, get_rest_effects
from oath.enums import MAX_ADVISERS


def create_initial_state(
    num_players: int = 4,
    seed: Optional[int] = None,
    first_game: bool = True,
    chronicle: Optional['ChronicleState'] = None,
    oath_goal: Optional[OathGoal] = None,
) -> GameState:
    """Create a fresh game state for a new game.

    Args:
        num_players: Number of players (2-6).
        seed: RNG seed for reproducibility.
        first_game: If True, use first-game defaults. Ignored if chronicle is provided.
        chronicle: Optional ChronicleState from a previous game's chronicle.
            When provided, uses the chronicled map, deck, oath goal, and player boards.
    """
    from oath.state.chronicle_state import ChronicleState

    rng = np.random.default_rng(seed)

    # Determine oath/successor goals
    if oath_goal is not None:
        # Explicit oath_goal overrides chronicle and default
        from oath.enums import OATH_TO_SUCCESSOR
        successor_goal = OATH_TO_SUCCESSOR.get(oath_goal, SuccessorGoal.MOST_SITES)
    elif chronicle is not None:
        oath_goal = chronicle.oath_goal
        successor_goal = chronicle.successor_goal
    else:
        oath_goal = OathGoal.SUPREMACY
        successor_goal = SuccessorGoal.MOST_SITES

    gs = GameState(
        num_players=num_players,
        rng=rng,
        oath_goal=oath_goal,
        successor_goal=successor_goal,
    )

    # Determine who is Chancellor this game
    # In a chronicle, the last winner becomes Chancellor
    chancellor_idx = 0
    if chronicle is not None and chronicle.last_winner is not None:
        chancellor_idx = chronicle.last_winner % num_players

    # Create players
    gs.players = []
    # Build non-Chancellor role list from chronicle player_boards
    non_chancellor_roles = []
    if chronicle is not None:
        non_chancellor_roles = list(chronicle.player_boards)
    board_idx = 0
    for i in range(num_players):
        if i == chancellor_idx:
            role = Role.CHANCELLOR
            supply = 7
            warbands_bank = MAX_WARBANDS_CHANCELLOR
        else:
            if board_idx < len(non_chancellor_roles):
                role = non_chancellor_roles[board_idx]
            else:
                role = Role.EXILE
            board_idx += 1
            supply = 7
            warbands_bank = MAX_WARBANDS_EXILE
        gs.players.append(PlayerState(
            role=role,
            supply=supply,
            warbands_bank=warbands_bank,
            color=i,
        ))

    # Turn order: Chancellor first, then others in order
    gs.turn_order = [chancellor_idx] + [i for i in range(num_players) if i != chancellor_idx]
    gs.current_player_index = chancellor_idx

    # Set up sites
    if chronicle is not None and chronicle.chronicled_sites:
        _setup_sites_from_chronicle(gs, chronicle, rng)
    elif first_game:
        _setup_sites_first_game(gs, rng)
    else:
        _setup_sites_first_game(gs, rng)  # Fallback

    # Build world deck
    if chronicle is not None and chronicle.world_deck:
        gs.world_deck = list(chronicle.world_deck)
    elif first_game:
        _build_first_game_deck(gs, rng)
    else:
        _build_full_deck(gs, rng)

    # Build relic deck
    if chronicle is not None and chronicle.relic_deck:
        gs.relic_deck = list(chronicle.relic_deck)
    elif first_game:
        relic_ids = list(get_first_game_relic_ids())
        rng.shuffle(relic_ids)
        gs.relic_deck = relic_ids
    else:
        relic_ids = list(get_first_game_relic_ids())
        rng.shuffle(relic_ids)
        gs.relic_deck = relic_ids

    # Place relics at faceup sites (setup step 16/19)
    for site_idx in range(len(gs.sites)):
        site = gs.sites[site_idx]
        if site.is_faceup and not site.relics:
            card_data = get_card(site.site_id)
            # Sites show "R" icons indicating how many relics
            # For simplicity, place 1 relic per faceup Cradle site
            if site.region == Region.CRADLE and gs.relic_deck:
                site.relics.append(gs.relic_deck.pop(0))

    # Set up favor banks (6 favor per suit to start, or 4 for 5-6 players)
    favor_per_bank = 4 if num_players >= 5 else 3
    gs.favor_banks = [favor_per_bank] * 6

    # Shared secrets
    gs.shared_secrets = 12

    # Banners start unclaimed with base tokens
    gs.peoples_favor_holder = None
    gs.peoples_favor_tokens = 1
    gs.darkest_secret_holder = None
    gs.darkest_secret_tokens = 1

    # Chancellor starts as Oathkeeper (on Oathkeeper side)
    gs.oathkeeper_holder = chancellor_idx
    gs.oathkeeper_side = TitleSide.OATHKEEPER

    # If Oathkeeper of Devotion, Chancellor starts with Darkest Secret
    if oath_goal == OathGoal.DEVOTION:
        gs.darkest_secret_holder = chancellor_idx
    # If Oathkeeper of People, Chancellor starts with People's Favor
    elif oath_goal == OathGoal.PEOPLE:
        gs.peoples_favor_holder = chancellor_idx

    # Place Chancellor starting warbands at site 0
    gs.players[chancellor_idx].pawn_site = 0
    gs.sites[0].ruling_player = chancellor_idx
    gs.sites[0].warbands = 3
    gs.sites[0].warband_color = 0  # Imperial color
    gs.players[chancellor_idx].warbands_board = 3
    gs.players[chancellor_idx].warbands_bank -= 3

    # Give Chancellor starting resources (2 favor + 1 secret)
    gs.players[chancellor_idx].favor = 2
    gs.players[chancellor_idx].secrets = 1
    gs.shared_secrets -= 1

    # Each non-Chancellor places 1 favor + 1 secret, 3 warbands on board
    exile_site = 1
    for i in range(num_players):
        if i == chancellor_idx:
            continue
        site_idx = min(exile_site, MAX_SITES - 1)
        exile_site += 1
        gs.players[i].pawn_site = site_idx
        gs.players[i].favor = 1
        gs.players[i].secrets = 1
        gs.shared_secrets -= 1
        # Exiles place 3 own-color warbands; Citizens place 3 purple
        gs.players[i].warbands_board = 3
        gs.players[i].warbands_bank -= 3

    # Deal starting cards (3 from bottom of world deck, keep 1 as adviser)
    for i in range(gs.num_players):
        if len(gs.world_deck) >= 3:
            drawn = [gs.world_deck.pop() for _ in range(3)]
            # Keep the first non-vision card as facedown adviser
            kept = None
            for card_id in drawn:
                card = get_card(card_id)
                if not card.is_vision:
                    kept = card_id
                    break
            if kept is None and drawn:
                kept = drawn[0]
            if kept is not None:
                slot = gs.players[i].first_empty_adviser_slot()
                if slot is not None:
                    gs.players[i].advisers[slot] = kept
                    gs.players[i].adviser_faceup[slot] = False
                drawn.remove(kept)
            # Discard the rest
            for card_id in drawn:
                region = gs.players[i].pawn_site
                pile_idx = min(gs.sites[region].region, 2)
                gs.discard_piles[pile_idx].append(card_id)

    # Start in wake phase
    gs.phase = Phase.WAKE
    gs.round_number = 1

    logger.info(
        "Game created: %d players, oath=%s, successor=%s, chancellor=P%d, seed=%s",
        num_players, oath_goal.name, successor_goal.name, chancellor_idx, seed,
    )
    return gs


def _setup_sites_first_game(gs: GameState, rng: np.random.Generator) -> None:
    """Set up sites for the first game."""
    site_ids = get_first_game_site_ids()
    regions = [Region.CRADLE, Region.CRADLE,
               Region.PROVINCES, Region.PROVINCES, Region.PROVINCES,
               Region.HINTERLAND, Region.HINTERLAND, Region.HINTERLAND]

    gs.sites = []
    for idx in range(MAX_SITES):
        site_id = site_ids[idx] if idx < len(site_ids) else 0
        card_data = get_card(site_id)
        site = SiteState(
            site_id=site_id,
            region=regions[idx],
            is_faceup=(regions[idx] == Region.CRADLE),
            capacity=card_data.capacity if card_data.capacity > 0 else 3,
            cards=[None, None, None],
            card_favor=[0, 0, 0],
            card_secrets=[0, 0, 0],
        )
        gs.sites.append(site)


def _setup_sites_from_chronicle(
    gs: GameState,
    chronicle: 'ChronicleState',
    rng: np.random.Generator,
) -> None:
    """Set up sites from chronicle state.

    Uses chronicled sites (those with edifices) in their original positions,
    fills remaining slots with site deck or defaults.
    """
    site_ids = get_first_game_site_ids()
    regions = [Region.CRADLE, Region.CRADLE,
               Region.PROVINCES, Region.PROVINCES, Region.PROVINCES,
               Region.HINTERLAND, Region.HINTERLAND, Region.HINTERLAND]

    gs.sites = []

    # Place chronicled sites first (they have edifices)
    chronicle_idx = 0
    for idx in range(MAX_SITES):
        if chronicle_idx < len(chronicle.chronicled_sites):
            snap = chronicle.chronicled_sites[chronicle_idx]
            card_data = get_card(snap.site_id)
            site = SiteState(
                site_id=snap.site_id,
                region=regions[idx],
                is_faceup=(regions[idx] == Region.CRADLE),
                capacity=card_data.capacity if card_data.capacity > 0 else 3,
                cards=[None, None, None],
                card_favor=[0, 0, 0],
                card_secrets=[0, 0, 0],
            )
            # Place chronicled cards at this site
            for slot, card_id in enumerate(snap.cards):
                if slot < site.capacity:
                    site.cards[slot] = card_id
            site.relics = list(snap.relics)
            gs.sites.append(site)
            chronicle_idx += 1
        else:
            # Fill with default site
            site_id = site_ids[idx] if idx < len(site_ids) else 0
            card_data = get_card(site_id)
            site = SiteState(
                site_id=site_id,
                region=regions[idx],
                is_faceup=(regions[idx] == Region.CRADLE),
                capacity=card_data.capacity if card_data.capacity > 0 else 3,
                cards=[None, None, None],
                card_favor=[0, 0, 0],
                card_secrets=[0, 0, 0],
            )
            gs.sites.append(site)


def _build_first_game_deck(gs: GameState, rng: np.random.Generator) -> None:
    """Build the world deck for the first game."""
    denizen_ids = get_first_game_denizen_ids()
    vision_ids = get_vision_ids()
    all_cards = list(denizen_ids)
    rng.shuffle(all_cards)

    # Place cards at Cradle sites
    card_idx = 0
    for site_idx in range(2):
        site = gs.sites[site_idx]
        for slot in range(site.capacity):
            if card_idx < len(all_cards):
                site.cards[slot] = all_cards[card_idx]
                card_idx += 1

    remaining = all_cards[card_idx:]
    for vid in vision_ids:
        pos = rng.integers(0, len(remaining) + 1)
        remaining.insert(pos, vid)

    gs.world_deck = remaining


def _build_full_deck(gs: GameState, rng: np.random.Generator) -> None:
    """Build the world deck using all denizens."""
    denizen_ids = get_all_denizen_ids()
    vision_ids = get_vision_ids()
    all_cards = list(denizen_ids)
    rng.shuffle(all_cards)

    card_idx = 0
    for site_idx in range(2):
        site = gs.sites[site_idx]
        for slot in range(site.capacity):
            if card_idx < len(all_cards) and site.cards[slot] is None:
                site.cards[slot] = all_cards[card_idx]
                card_idx += 1

    remaining = all_cards[card_idx:]
    for vid in vision_ids:
        pos = rng.integers(0, len(remaining) + 1)
        remaining.insert(pos, vid)

    gs.world_deck = remaining


def advance_turn(gs: GameState) -> GameState:
    """Advance to the next player's turn."""
    gs.supply_spent_this_turn = 0
    gs.actions_taken_this_turn = 0

    current_pos = gs.turn_order.index(gs.current_player_index)
    next_pos = (current_pos + 1) % len(gs.turn_order)

    if next_pos == 0:
        # End of round
        gs.turn_in_round = 0
        logger.debug("End of round %d", gs.round_number)
        _end_of_round(gs)
    else:
        gs.turn_in_round = next_pos
        gs.current_player_index = gs.turn_order[next_pos]
        gs.phase = Phase.WAKE
        player = gs.players[gs.current_player_index]
        logger.debug(
            "Turn -> P%d (%s) round=%d",
            gs.current_player_index, player.role.name, gs.round_number,
        )

    return gs


def do_wake_phase(gs: GameState) -> GameState:
    """Execute wake phase: People's Favor power, site powers, then WAKE effects.

    Order per rules:
    1. People's Favor wake power (§4.1.1)
    2. Site powers (§4.1.4)
    3. Card wake effects on faceup advisers
    """
    player = gs.current_player
    pi = gs.current_player_index

    # ── 1. People's Favor wake power (§4.1.1) ──────────────────────
    _resolve_peoples_favor_wake(gs, pi)

    # ── 2. Site powers (§4.1.4) ─────────────────────────────────────
    _resolve_site_power_wake(gs, pi)

    # ── 3. Card wake effects on faceup advisers ─────────────────────
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None and player.adviser_faceup[slot]:
            for effect in get_wake_effects(card_id):
                if effect.condition(gs, pi):
                    gs = effect.execute(gs, pi)
    return gs


def _resolve_peoples_favor_wake(gs: GameState, player_index: int) -> None:
    """Auto-resolve People's Favor wake power (§4.1.1).

    §4.1.1.I: Place 1 favor from PF banner onto the bank with least favor.
               On ties, pick the first bank in SUIT_CLOCKWISE_ORDER.
               If the PF banner has 0 tokens, skip.
    §4.1.1.II: If PF is on Mob side, repeat step I once more.
    §4.1.1.III: If PF now has 6+ tokens, flip to Mob. If under 6 and Mob, flip back.

    Heuristic: always PLACE (move 1 token from PF banner to least-filled bank).
    """
    if gs.peoples_favor_holder != player_index:
        return

    iterations = 2 if gs.peoples_favor_is_mob else 1

    for _ in range(iterations):
        if gs.peoples_favor_tokens <= 0:
            break

        # Find the bank with the least favor (ties: first in clockwise order)
        min_favor = None
        min_suit = None
        for suit in SUIT_CLOCKWISE_ORDER:
            bank_val = gs.favor_banks[suit]
            if min_favor is None or bank_val < min_favor:
                min_favor = bank_val
                min_suit = suit

        if min_suit is not None:
            gs.peoples_favor_tokens -= 1
            gs.favor_banks[min_suit] += 1
            logger.debug(
                "PF wake: P%d placed 1 favor on %s bank (now %d), PF tokens=%d",
                player_index, Suit(min_suit).name,
                gs.favor_banks[min_suit], gs.peoples_favor_tokens,
            )

    # §4.1.1.III: Check Mob flip condition
    if gs.peoples_favor_tokens >= 6 and not gs.peoples_favor_is_mob:
        gs.peoples_favor_is_mob = True
        logger.debug("PF flipped to MOB side (tokens=%d)", gs.peoples_favor_tokens)
    elif gs.peoples_favor_tokens < 6 and gs.peoples_favor_is_mob:
        gs.peoples_favor_is_mob = False
        logger.debug("PF flipped back from MOB side (tokens=%d)", gs.peoples_favor_tokens)


def _resolve_site_power_wake(gs: GameState, player_index: int) -> None:
    """Auto-resolve site powers during wake phase (§4.1.4).

    Salt Flats, Mine, Drowned City: take 1 favor or 1 secret from shared bank.
    Heuristic: always take 1 secret (more valuable for RL).
    """
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    if site.site_id in RESOURCE_SITE_IDS:
        if gs.shared_secrets > 0:
            gs.shared_secrets -= 1
            player.secrets += 1
            logger.debug(
                "Site power: P%d at %s took 1 secret (now %d)",
                player_index, get_card(site.site_id).name, player.secrets,
            )
        else:
            # Fall back to favor if no secrets available
            # (favor comes from the player's own supply conceptually,
            # but the rule says "from the bank" — we give 1 favor)
            player.favor += 1
            logger.debug(
                "Site power: P%d at %s took 1 favor (no secrets, now %d)",
                player_index, get_card(site.site_id).name, player.favor,
            )


def start_act_phase(gs: GameState) -> GameState:
    """Transition from wake to act phase."""
    gs.phase = Phase.ACT
    return gs


def do_rest_phase(gs: GameState) -> GameState:
    """Execute the automated rest phase for the current player.

    Supply refresh follows §4.3.3-4.3.4:
    1. Refresh: set supply to the position based on warbands in bank.
    2. Save: add unspent supply (what remains after spending during act phase),
       capped at MAX_SUPPLY.
    """
    player = gs.current_player
    pi = gs.current_player_index
    unspent_supply = player.supply  # Supply remaining after act phase
    refresh = _calculate_supply_refresh(gs, pi)
    player.supply = min(refresh + unspent_supply, MAX_SUPPLY)

    # Trigger REST effects on faceup advisers
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None and player.adviser_faceup[slot]:
            for effect in get_rest_effects(card_id):
                if effect.condition(gs, pi):
                    gs = effect.execute(gs, pi)

    return gs


def _calculate_supply_refresh(gs: GameState, player_index: int) -> int:
    """Calculate supply refresh based on role and advisers.

    §4.3.3: Chancellor refreshes to 6. Exiles refresh to (6 - num_advisers).
    Citizens refresh to the Chancellor's supply value (same formula as Chancellor).
    """
    player = gs.players[player_index]
    if player.role == Role.CHANCELLOR:
        return 6
    elif player.role == Role.CITIZEN:
        # Citizens refresh to the Chancellor's supply value (§4.3.3)
        chancellor_idx = gs.chancellor_index
        return _calculate_supply_refresh(gs, chancellor_idx)
    else:
        # Exiles get supply = 6 - number of advisers
        return max(1, 6 - player.num_advisers)


def _end_of_round(gs: GameState) -> GameState:
    """Process end-of-round logic."""
    from oath.engine.win_conditions import check_end_of_round_win

    gs.round_number += 1

    if gs.round_number > MAX_ROUNDS:
        gs.is_game_over = True
        if gs.winner is None:
            gs.winner = gs.oathkeeper_holder
        logger.info(
            "Game over (max rounds): winner=P%s, win_type=%s",
            gs.winner, gs.win_type,
        )
        return gs

    # Check if game can end (round 5+)
    if gs.round_number >= 5:
        result = check_end_of_round_win(gs)
        if result is not None:
            gs.is_game_over = True
            gs.winner = result
            logger.info(
                "Game over (end-of-round): winner=P%d, win_type=%s, round=%d",
                result, gs.win_type, gs.round_number,
            )

    # Start new round
    gs.current_player_index = gs.turn_order[0]
    gs.phase = Phase.WAKE

    return gs

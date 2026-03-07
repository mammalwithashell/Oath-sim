"""Main game loop and setup for Oath simulator."""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.enums import (
    Role, Region, Phase, OathGoal, SuccessorGoal, TitleSide,
    Suit, MAX_SITES, MAX_WARBANDS_CHANCELLOR, MAX_WARBANDS_EXILE,
    MAX_ROUNDS, ActionType,
)
from oath.state.game_state import GameState, ActionRecord
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.cards.database import (
    get_card, get_first_game_denizen_ids, get_first_game_site_ids,
    get_first_game_relic_ids, get_vision_ids, get_all_denizen_ids,
)
from oath.cards.effects import get_wake_effects, get_rest_effects
from oath.enums import MAX_ADVISERS


def create_initial_state(
    num_players: int = 4,
    seed: Optional[int] = None,
    first_game: bool = True,
    chronicle: Optional['ChronicleState'] = None,
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
    if chronicle is not None:
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

    # Create players
    gs.players = []
    for i in range(num_players):
        if i == 0:
            role = Role.CHANCELLOR
            supply = 7
            warbands_bank = MAX_WARBANDS_CHANCELLOR
        else:
            # Use chronicle player boards if available
            if chronicle is not None and (i - 1) < len(chronicle.player_boards):
                role = chronicle.player_boards[i - 1]
            else:
                role = Role.EXILE
            supply = 7
            warbands_bank = MAX_WARBANDS_EXILE
        gs.players.append(PlayerState(
            role=role,
            supply=supply,
            warbands_bank=warbands_bank,
            color=i,
        ))

    # Turn order: Chancellor first, then others in order
    gs.turn_order = list(range(num_players))
    gs.current_player_index = 0

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
    gs.oathkeeper_holder = 0
    gs.oathkeeper_side = TitleSide.OATHKEEPER

    # If Oathkeeper of Devotion, Chancellor starts with Darkest Secret
    if oath_goal == OathGoal.DEVOTION:
        gs.darkest_secret_holder = 0
    # If Oathkeeper of People, Chancellor starts with People's Favor
    elif oath_goal == OathGoal.PEOPLE:
        gs.peoples_favor_holder = 0

    # Place starting warbands
    gs.players[0].pawn_site = 0
    gs.sites[0].ruling_player = 0
    gs.sites[0].warbands = 3
    gs.players[0].warbands_board = 3
    gs.players[0].warbands_bank -= 3

    # Give chancellor starting resources (2 favor + 1 secret)
    gs.players[0].favor = 2
    gs.players[0].secrets = 1
    gs.shared_secrets -= 1

    # Each Exile/Citizen places 1 favor + 1 secret, 3 warbands on board
    for i in range(1, num_players):
        site_idx = min(i, MAX_SITES - 1)
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
        _end_of_round(gs)
    else:
        gs.turn_in_round = next_pos
        gs.current_player_index = gs.turn_order[next_pos]
        gs.phase = Phase.WAKE

    return gs


def do_wake_phase(gs: GameState) -> GameState:
    """Execute wake phase: trigger WAKE effects on faceup advisers."""
    player = gs.current_player
    pi = gs.current_player_index
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None and player.adviser_faceup[slot]:
            for effect in get_wake_effects(card_id):
                if effect.condition(gs, pi):
                    gs = effect.execute(gs, pi)
    return gs


def start_act_phase(gs: GameState) -> GameState:
    """Transition from wake to act phase."""
    gs.phase = Phase.ACT
    return gs


def do_rest_phase(gs: GameState) -> GameState:
    """Execute the automated rest phase for the current player."""
    player = gs.current_player
    pi = gs.current_player_index
    player.supply = _calculate_supply_refresh(gs, pi)

    # Trigger REST effects on faceup advisers
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None and player.adviser_faceup[slot]:
            for effect in get_rest_effects(card_id):
                if effect.condition(gs, pi):
                    gs = effect.execute(gs, pi)

    return gs


def _calculate_supply_refresh(gs: GameState, player_index: int) -> int:
    """Calculate supply refresh based on role and advisers."""
    player = gs.players[player_index]
    if player.role == Role.CHANCELLOR:
        return 6
    else:
        # Exiles get supply = 6 - number of advisers
        return max(1, 6 - player.num_advisers)


def _end_of_round(gs: GameState) -> GameState:
    """Process end-of-round logic."""
    from oath.engine.win_conditions import check_end_of_round_win

    gs.round_number += 1

    if gs.round_number > MAX_ROUNDS:
        gs.is_game_over = True
        # Chancellor wins if no usurper
        if gs.winner is None:
            gs.winner = gs.oathkeeper_holder
        return gs

    # Check if game can end (round 5+)
    if gs.round_number >= 5:
        result = check_end_of_round_win(gs)
        if result is not None:
            gs.is_game_over = True
            gs.winner = result

    # Start new round
    gs.current_player_index = gs.turn_order[0]
    gs.phase = Phase.WAKE

    return gs

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


def create_initial_state(
    num_players: int = 4,
    seed: Optional[int] = None,
    first_game: bool = True,
) -> GameState:
    """Create a fresh game state for a new game."""
    rng = np.random.default_rng(seed)

    gs = GameState(
        num_players=num_players,
        rng=rng,
        oath_goal=OathGoal.SUPREMACY,
        successor_goal=SuccessorGoal.MOST_SITES,
    )

    # Create players
    gs.players = []
    for i in range(num_players):
        if i == 0:
            role = Role.CHANCELLOR
            supply = 7
            warbands_bank = MAX_WARBANDS_CHANCELLOR
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

    # Turn order: Chancellor first, then exiles in order
    gs.turn_order = list(range(num_players))
    gs.current_player_index = 0

    # Set up sites
    if first_game:
        site_ids = get_first_game_site_ids()
    else:
        site_ids = get_first_game_site_ids()  # Placeholder

    gs.sites = []
    regions = [Region.CRADLE, Region.CRADLE,
               Region.PROVINCES, Region.PROVINCES, Region.PROVINCES,
               Region.HINTERLAND, Region.HINTERLAND, Region.HINTERLAND]

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

    # Build world deck
    if first_game:
        denizen_ids = get_first_game_denizen_ids()
    else:
        denizen_ids = get_all_denizen_ids()

    # Shuffle visions into the world deck
    vision_ids = get_vision_ids()
    all_cards = list(denizen_ids)  # copy
    rng.shuffle(all_cards)

    # Place some cards at Cradle sites (faceup sites start with cards)
    card_idx = 0
    for site_idx in range(2):  # Cradle sites
        site = gs.sites[site_idx]
        for slot in range(site.capacity):
            if card_idx < len(all_cards):
                site.cards[slot] = all_cards[card_idx]
                card_data = get_card(all_cards[card_idx])
                card_idx += 1

    # Remaining cards form the world deck
    remaining = all_cards[card_idx:]

    # Insert visions randomly into the deck
    for vid in vision_ids:
        pos = rng.integers(0, len(remaining) + 1)
        remaining.insert(pos, vid)

    gs.world_deck = remaining

    # Build relic deck
    if first_game:
        relic_ids = list(get_first_game_relic_ids())
    else:
        relic_ids = list(get_first_game_relic_ids())
    rng.shuffle(relic_ids)
    gs.relic_deck = relic_ids

    # Place relics at some faceup sites
    for site_idx in range(2):
        site = gs.sites[site_idx]
        if gs.relic_deck:
            site.relics.append(gs.relic_deck.pop(0))

    # Set up favor banks (6 favor per suit to start)
    gs.favor_banks = [6] * 6

    # Shared secrets
    gs.shared_secrets = 12

    # Banners start unclaimed
    gs.peoples_favor_holder = None
    gs.peoples_favor_tokens = 1
    gs.darkest_secret_holder = None
    gs.darkest_secret_tokens = 1

    # Chancellor starts as Oathkeeper
    gs.oathkeeper_holder = 0
    gs.oathkeeper_side = TitleSide.OATHKEEPER

    # Place starting warbands
    # Chancellor gets some warbands at Cradle
    gs.players[0].pawn_site = 0
    gs.sites[0].ruling_player = 0
    gs.sites[0].warbands = 3
    gs.players[0].warbands_board = 3
    gs.players[0].warbands_bank -= 3

    # Give chancellor a starting secret
    gs.players[0].secrets = 1
    gs.shared_secrets -= 1

    # Exiles start at different sites
    for i in range(1, num_players):
        site_idx = min(i, MAX_SITES - 1)
        gs.players[i].pawn_site = site_idx
        gs.players[i].secrets = 1
        gs.shared_secrets -= 1

    # Start in wake phase
    gs.phase = Phase.WAKE
    gs.round_number = 1

    return gs


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


def start_act_phase(gs: GameState) -> GameState:
    """Transition from wake to act phase."""
    gs.phase = Phase.ACT
    return gs


def do_rest_phase(gs: GameState) -> GameState:
    """Execute the automated rest phase for the current player."""
    player = gs.current_player
    player.supply = _calculate_supply_refresh(gs, gs.current_player_index)
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

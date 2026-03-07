"""Reward shaping for Oath RL environment."""

from __future__ import annotations

from oath.env.action_decoder import DecodedAction
from oath.state.game_state import GameState
from oath.engine.win_conditions import _count_relics_and_banners


def compute_reward(
    prev_state: GameState,
    action: DecodedAction,
    new_state: GameState,
    player_idx: int,
) -> float:
    """Compute shaped reward for a player after an action."""
    reward = 0.0

    # Terminal rewards
    if new_state.is_game_over:
        if new_state.winner == player_idx:
            return 1.0
        else:
            return -1.0

    SCALE = 0.01

    # Gained Oathkeeper title
    if (new_state.oathkeeper_holder == player_idx and
            prev_state.oathkeeper_holder != player_idx):
        reward += 3.0 * SCALE

    # Lost Oathkeeper title
    if (prev_state.oathkeeper_holder == player_idx and
            new_state.oathkeeper_holder != player_idx):
        reward -= 2.0 * SCALE

    # Took a site
    new_sites = new_state.count_sites_ruled(player_idx)
    old_sites = prev_state.count_sites_ruled(player_idx)
    reward += (new_sites - old_sites) * 1.0 * SCALE

    # Recovered a relic or banner
    new_relics = len(new_state.players[player_idx].relics)
    old_relics = len(prev_state.players[player_idx].relics)
    reward += (new_relics - old_relics) * 0.5 * SCALE

    # Vision revealed
    if (new_state.players[player_idx].revealed_vision is not None and
            prev_state.players[player_idx].revealed_vision is None):
        reward += 1.0 * SCALE

    # Got banished (check if player moved far and lost resources)
    new_player = new_state.players[player_idx]
    old_player = prev_state.players[player_idx]
    if (new_player.favor < old_player.favor // 2 and
            new_player.pawn_site != old_player.pawn_site):
        reward -= 1.5 * SCALE

    return reward

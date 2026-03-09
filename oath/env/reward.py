"""Reward shaping for Oath RL environment.

Includes both role-agnostic and role-aware reward signals to teach
agents different strategies based on their current role.
"""

from __future__ import annotations

from oath.enums import Role, SuccessorGoal
from oath.env.action_decoder import DecodedAction
from oath.state.game_state import GameState
from oath.engine.win_conditions import _count_relics_and_banners, _check_vision_condition


SCALE = 0.01


def compute_reward(
    prev_state: GameState,
    action: DecodedAction,
    new_state: GameState,
    player_idx: int,
) -> float:
    """Compute shaped reward for a player after an action."""
    reward = 0.0

    # Terminal rewards (deferred during vow phase — winner gets +1.0 via _finalize_vow)
    if new_state.is_game_over and not new_state.in_vow_phase and new_state.vowed_oath is None:
        if new_state.winner == player_idx:
            return 1.0
        else:
            return -1.0

    new_player = new_state.players[player_idx]
    old_player = prev_state.players[player_idx]

    # ── Role-agnostic rewards ──────────────────────────────────────

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
    new_relics = len(new_player.relics)
    old_relics = len(old_player.relics)
    reward += (new_relics - old_relics) * 0.5 * SCALE

    # Got banished (lost favor and moved)
    if (new_player.favor < old_player.favor // 2 and
            new_player.pawn_site != old_player.pawn_site):
        reward -= 1.5 * SCALE

    # ── Role-specific rewards ─────────────────────────────────────

    if new_player.role == Role.EXILE:
        reward += _exile_rewards(prev_state, new_state, player_idx)
    elif new_player.role == Role.CITIZEN:
        reward += _citizen_rewards(prev_state, new_state, player_idx)
    elif new_player.role == Role.CHANCELLOR:
        reward += _chancellor_rewards(prev_state, new_state, player_idx)

    # ── Citizenship transition rewards ────────────────────────────

    reward += _citizenship_transition_rewards(prev_state, new_state, player_idx)

    return reward


def _exile_rewards(
    prev_state: GameState, new_state: GameState, player_idx: int,
) -> float:
    """Rewards specific to Exile strategy: vision pursuit."""
    reward = 0.0
    new_player = new_state.players[player_idx]
    old_player = prev_state.players[player_idx]

    # Revealed a vision (stronger signal than role-agnostic version)
    if (new_player.revealed_vision is not None and
            old_player.revealed_vision is None):
        reward += 2.0 * SCALE

    # Meeting vision condition
    if new_player.revealed_vision is not None:
        now_met = _check_vision_condition(
            new_state, player_idx, new_player.revealed_vision)
        was_met = False
        if old_player.revealed_vision is not None:
            was_met = _check_vision_condition(
                prev_state, player_idx, old_player.revealed_vision)
        if now_met and not was_met:
            reward += 3.0 * SCALE
        elif was_met and not now_met:
            reward -= 2.0 * SCALE

    # Visions drawn progress (global — exiles benefit from visions entering play)
    if new_state.visions_drawn > prev_state.visions_drawn:
        reward += 0.5 * SCALE

    return reward


def _citizen_rewards(
    prev_state: GameState, new_state: GameState, player_idx: int,
) -> float:
    """Rewards specific to Citizen strategy: beat Chancellor on successor goal."""
    reward = 0.0
    goal = new_state.successor_goal

    chanc_idx = new_state.chancellor_index

    if goal == SuccessorGoal.PEOPLES_FAVOR:
        if (new_state.peoples_favor_holder == player_idx and
                prev_state.peoples_favor_holder != player_idx):
            reward += 3.0 * SCALE
        elif (prev_state.peoples_favor_holder == player_idx and
                new_state.peoples_favor_holder != player_idx):
            reward -= 3.0 * SCALE

    elif goal == SuccessorGoal.DARKEST_SECRET:
        if (new_state.darkest_secret_holder == player_idx and
                prev_state.darkest_secret_holder != player_idx):
            reward += 3.0 * SCALE
        elif (prev_state.darkest_secret_holder == player_idx and
                new_state.darkest_secret_holder != player_idx):
            reward -= 3.0 * SCALE

    elif goal == SuccessorGoal.MOST_RELICS_BANNERS:
        my_count = _count_relics_and_banners(new_state, player_idx)
        chanc_count = _count_relics_and_banners(new_state, chanc_idx)
        old_my = _count_relics_and_banners(prev_state, player_idx)
        old_chanc = _count_relics_and_banners(prev_state, prev_state.chancellor_index)
        new_gap = my_count - chanc_count
        old_gap = old_my - old_chanc
        reward += (new_gap - old_gap) * 1.5 * SCALE

    elif goal == SuccessorGoal.GRAND_SCEPTER:
        from oath.cards.database import GRAND_SCEPTER_ID
        has_now = GRAND_SCEPTER_ID in new_state.players[player_idx].relics
        had_before = GRAND_SCEPTER_ID in prev_state.players[player_idx].relics
        if has_now and not had_before:
            reward += 3.0 * SCALE
        elif had_before and not has_now:
            reward -= 3.0 * SCALE

    return reward


def _chancellor_rewards(
    prev_state: GameState, new_state: GameState, player_idx: int,
) -> float:
    """Rewards specific to Chancellor: maintain Oathkeeper and deny opponents."""
    reward = 0.0

    # Penalty for any Exile getting closer to vision win
    for i in range(new_state.num_players):
        if i == player_idx:
            continue
        opp = new_state.players[i]
        old_opp = prev_state.players[i]
        if opp.role == Role.EXILE:
            # Opponent revealed a vision = threat
            if (opp.revealed_vision is not None and
                    old_opp.revealed_vision is None):
                reward -= 1.0 * SCALE

    # Reward for maintaining Oathkeeper across turns
    if (new_state.oathkeeper_holder == player_idx and
            prev_state.oathkeeper_holder == player_idx):
        reward += 0.2 * SCALE

    return reward


def _citizenship_transition_rewards(
    prev_state: GameState, new_state: GameState, player_idx: int,
) -> float:
    """Rewards for role transitions (accepting/declining citizenship, self-exiling)."""
    reward = 0.0
    old_role = prev_state.players[player_idx].role
    new_role = new_state.players[player_idx].role

    if old_role == Role.EXILE and new_role == Role.CITIZEN:
        # Accepted citizenship — reward if already meeting successor goal
        from oath.engine.win_conditions import _check_successor_goal
        if _check_successor_goal(new_state, player_idx):
            reward += 2.0 * SCALE

    # Self-exile: no immediate shaping (let terminal reward handle it)

    return reward

"""Observation tensor encoder for Oath simulator.

Encodes GameState into a fixed-size float tensor suitable for neural networks.
The observation is player-relative: the observing player is always index 0.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.enums import (
    Suit, Region, Role, OathGoal, SuccessorGoal, TitleSide, Phase,
    MAX_SITES, MAX_CARDS_PER_SITE, MAX_ADVISERS, MAX_RELICS_HELD,
    MAX_RELICS_PER_SITE, MAX_RELIQUARY, MAX_PLAYERS, MAX_ROUNDS,
    MAX_FAVOR_TOTAL, MAX_SECRETS_TOTAL, MAX_VISIONS_DRAWN,
    MAX_WARBANDS_CHANCELLOR, NUM_SUITS, NUM_ACTIONS,
    NUM_CARD_IDS,
)
from oath.state.game_state import GameState
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.cards.database import get_card

# Observation size constants
CARD_ENCODING_SIZE = 14
GLOBAL_SIZE = 86
SITE_SIZE = 100
PLAYER_SIZE = 167
DISCARD_TOPS_SIZE = 42
COMM_SIZE = 75
TURN_CONTEXT_SIZE = 14
WIN_PROXIMITY_SIZE = 30
ACTION_HISTORY_SIZE = 200
OBS_SIZE = 2249  # Total without action mask
TOTAL_OBS_SIZE = 2386  # With action mask (2249 + 137)


def encode_observation(gs: GameState, player_index: int) -> dict:
    """Encode game state into observation dict for a specific player.

    Returns dict with:
        - "observation": np.ndarray of shape (2248,)
        - "action_mask": np.ndarray of shape (123,)
        - "card_ids": dict of integer arrays for embedding lookup
    """
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    offset = 0

    # Global state (85)
    offset = _encode_global(gs, obs, offset)

    # Map (8 × 100 = 800)
    offset = _encode_map(gs, obs, offset, player_index)

    # Self player (167)
    offset = _encode_player(gs, obs, offset, player_index, player_index, is_self=True)

    # Other players (5 × 167 = 835)
    other_indices = _get_relative_player_order(gs, player_index)
    for other_idx in other_indices:
        if other_idx is not None and other_idx < gs.num_players:
            offset = _encode_player(gs, obs, offset, other_idx, player_index, is_self=False)
        else:
            offset += PLAYER_SIZE  # Zero-padded

    # Discard tops (42)
    offset = _encode_discard_tops(gs, obs, offset)

    # Communication (75) — stub zeros
    offset += COMM_SIZE

    # Turn context (14)
    offset = _encode_turn_context(gs, obs, offset)

    # Win proximity (30)
    offset = _encode_win_proximity(gs, obs, offset, player_index)

    # Action history (200)
    offset = _encode_action_history(gs, obs, offset, player_index)

    assert offset == OBS_SIZE, f"Observation offset mismatch: {offset} != {OBS_SIZE}"

    # Action mask computed separately
    from oath.env.action_decoder import ActionDecoder
    decoder = ActionDecoder()
    mask = decoder.get_legal_mask(gs, player_index)

    # Card IDs for embedding lookup
    card_ids = _extract_card_ids(gs, player_index)

    return {
        "observation": obs,
        "action_mask": mask,
        "card_ids": card_ids,
    }


def _encode_card(obs: np.ndarray, offset: int, card_id: Optional[int],
                 faceup: bool = True, is_self: bool = True,
                 favor_on: int = 0, secrets_on: int = 0) -> int:
    """Encode a single card into the observation tensor. Returns new offset."""
    if card_id is None or card_id == 0:
        return offset + CARD_ENCODING_SIZE

    card_data = get_card(card_id)

    # If hidden (facedown belonging to other player), only show is_present
    if not faceup and not is_self:
        obs[offset + 6] = 1.0  # is_present
        return offset + CARD_ENCODING_SIZE

    # Suit one-hot (6)
    if card_data.suit is not None:
        obs[offset + int(card_data.suit)] = 1.0

    obs[offset + 6] = 1.0  # is_present
    obs[offset + 7] = 1.0 if faceup else 0.0
    obs[offset + 8] = 1.0 if card_data.is_vision else 0.0
    obs[offset + 9] = 1.0 if card_data.is_edifice else 0.0
    obs[offset + 10] = 0.0  # is_ruin (tracked separately)
    obs[offset + 11] = favor_on / MAX_FAVOR_TOTAL if MAX_FAVOR_TOTAL > 0 else 0.0
    obs[offset + 12] = secrets_on / MAX_SECRETS_TOTAL if MAX_SECRETS_TOTAL > 0 else 0.0
    # offset + 13 = reserved

    return offset + CARD_ENCODING_SIZE


def _encode_global(gs: GameState, obs: np.ndarray, offset: int) -> int:
    """Encode global state (85 floats)."""
    start = offset
    obs[offset] = gs.round_number / MAX_ROUNDS; offset += 1
    obs[offset] = gs.visions_drawn / MAX_VISIONS_DRAWN; offset += 1
    from oath.engine.actions import search_cost
    cost = search_cost(gs)
    obs[offset] = (cost - 2) / 2.0; offset += 1

    # Oath goal one-hot (4)
    obs[offset + int(gs.oath_goal)] = 1.0; offset += 4

    # Successor goal one-hot (5) — includes GRAND_SCEPTER
    obs[offset + int(gs.successor_goal)] = 1.0; offset += 5

    # Favor banks (6)
    for i in range(NUM_SUITS):
        obs[offset + i] = gs.favor_banks[i] / MAX_FAVOR_TOTAL
    offset += 6

    obs[offset] = len(gs.world_deck) / 200.0; offset += 1

    # Discard pile sizes (3)
    for i in range(3):
        obs[offset + i] = len(gs.discard_piles[i]) / 100.0
    offset += 3

    obs[offset] = len(gs.relic_deck) / 20.0; offset += 1
    obs[offset] = gs.peoples_favor_tokens / 12.0; offset += 1
    obs[offset] = gs.darkest_secret_tokens / 12.0; offset += 1

    # Peoples favor side one-hot (2)
    if not gs.peoples_favor_is_mob:
        obs[offset] = 1.0
    else:
        obs[offset + 1] = 1.0
    offset += 2

    obs[offset] = 1.0 if gs.round_number >= 5 else 0.0; offset += 1
    from oath.engine.win_conditions import _end_probability
    obs[offset] = _end_probability(gs.round_number); offset += 1
    obs[offset] = gs.num_players / MAX_PLAYERS; offset += 1

    # Reliquary relics (4 × 14 = 56)
    for i in range(MAX_RELIQUARY):
        if i < len(gs.reliquary):
            offset = _encode_card(obs, offset, gs.reliquary[i])
        else:
            offset += CARD_ENCODING_SIZE

    assert offset - start == GLOBAL_SIZE, f"Global: {offset - start} != {GLOBAL_SIZE}"
    return offset


def _encode_map(gs: GameState, obs: np.ndarray, offset: int, player_index: int) -> int:
    """Encode map state (8 × 100 = 800)."""
    for site_idx in range(MAX_SITES):
        start = offset
        site = gs.sites[site_idx] if site_idx < len(gs.sites) else None

        if site is None:
            offset += SITE_SIZE
            continue

        # Region one-hot (3)
        obs[offset + int(site.region)] = 1.0; offset += 3

        obs[offset] = 1.0 if site.is_faceup else 0.0; offset += 1
        obs[offset] = 1.0; offset += 1  # is_present
        obs[offset] = site.capacity / MAX_CARDS_PER_SITE; offset += 1

        # Cards at site (3 × 14 = 42)
        for slot in range(MAX_CARDS_PER_SITE):
            card_id = site.cards[slot] if slot < len(site.cards) else None
            favor = site.card_favor[slot] if slot < len(site.card_favor) else 0
            secrets = site.card_secrets[slot] if slot < len(site.card_secrets) else 0
            if site.is_faceup:
                offset = _encode_card(obs, offset, card_id, faceup=True,
                                     favor_on=favor, secrets_on=secrets)
            else:
                offset += CARD_ENCODING_SIZE

        # Ruling player one-hot (6)
        if site.ruling_player is not None:
            rel_idx = _relative_index(site.ruling_player, player_index, gs.num_players)
            if rel_idx < MAX_PLAYERS:
                obs[offset + rel_idx] = 1.0
        offset += 6

        obs[offset] = site.warbands / MAX_WARBANDS_CHANCELLOR; offset += 1

        # Relics at site (3 × 14 = 42)
        for slot in range(MAX_RELICS_PER_SITE):
            if slot < len(site.relics):
                # Relics at sites are facedown (hidden)
                offset = _encode_card(obs, offset, site.relics[slot],
                                     faceup=False, is_self=False)
            else:
                offset += CARD_ENCODING_SIZE

        obs[offset] = site.site_favor / MAX_FAVOR_TOTAL; offset += 1
        obs[offset] = site.site_secrets / MAX_SECRETS_TOTAL; offset += 1
        obs[offset] = 1.0 if not site.is_ruled and site.is_faceup else 0.0; offset += 1

        assert offset - start == SITE_SIZE, f"Site: {offset - start} != {SITE_SIZE}"

    return offset


def _encode_player(gs: GameState, obs: np.ndarray, offset: int,
                   player_idx: int, observer_idx: int, is_self: bool) -> int:
    """Encode a single player (167 floats)."""
    start = offset
    player = gs.players[player_idx]

    obs[offset] = 1.0; offset += 1  # is_active

    # Role one-hot (3)
    obs[offset + int(player.role)] = 1.0; offset += 3

    # Pawn location one-hot (8)
    obs[offset + player.pawn_site] = 1.0; offset += 8

    obs[offset] = player.supply / 9.0; offset += 1
    obs[offset] = player.warbands_board / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = player.warbands_bank / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = player.favor / MAX_FAVOR_TOTAL; offset += 1
    obs[offset] = player.secrets / MAX_SECRETS_TOTAL; offset += 1

    # Advisers (3 × 14 = 42)
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        faceup = player.adviser_faceup[slot] if slot < len(player.adviser_faceup) else False
        offset = _encode_card(obs, offset, card_id, faceup=faceup, is_self=is_self)

    # Relics held (6 × 14 = 84)
    for slot in range(6):
        if slot < len(player.relics):
            offset = _encode_card(obs, offset, player.relics[slot], faceup=True, is_self=is_self)
        else:
            offset += CARD_ENCODING_SIZE

    obs[offset] = 1.0 if gs.oathkeeper_holder == player_idx else 0.0; offset += 1

    # Title side one-hot (2)
    if gs.oathkeeper_holder == player_idx:
        obs[offset + int(gs.oathkeeper_side)] = 1.0
    offset += 2

    obs[offset] = 1.0 if gs.peoples_favor_holder == player_idx else 0.0; offset += 1
    obs[offset] = 1.0 if gs.darkest_secret_holder == player_idx else 0.0; offset += 1

    # Grand scepter
    has_scepter = 211 in player.relics  # Grand Scepter card_id
    obs[offset] = 1.0 if has_scepter else 0.0; offset += 1

    # Revealed vision (14)
    offset = _encode_card(obs, offset, player.revealed_vision,
                         faceup=(player.revealed_vision is not None), is_self=is_self)

    obs[offset] = gs.count_sites_ruled(player_idx) / MAX_SITES; offset += 1

    from oath.engine.win_conditions import _count_relics_and_banners
    obs[offset] = _count_relics_and_banners(gs, player_idx) / 8.0; offset += 1

    obs[offset] = 1.0 if gs.current_player_index == player_idx else 0.0; offset += 1
    offset += 1  # reserved

    assert offset - start == PLAYER_SIZE, f"Player: {offset - start} != {PLAYER_SIZE}"
    return offset


def _encode_discard_tops(gs: GameState, obs: np.ndarray, offset: int) -> int:
    """Encode top cards of discard piles (3 × 14 = 42)."""
    for i in range(3):
        pile = gs.discard_piles[i]
        if pile:
            offset = _encode_card(obs, offset, pile[-1], faceup=True)
        else:
            offset += CARD_ENCODING_SIZE
    return offset


def _encode_turn_context(gs: GameState, obs: np.ndarray, offset: int) -> int:
    """Encode turn context (14 floats)."""
    start = offset
    cs = gs.compound_state

    from oath.enums import CompoundStateType
    obs[offset] = 1.0 if (cs and cs.state_type == CompoundStateType.SEARCH_CHOOSE) else 0.0; offset += 1
    obs[offset] = 1.0 if (cs and cs.state_type == CompoundStateType.CAMPAIGN_TARGETS) else 0.0; offset += 1
    obs[offset] = 1.0 if (cs and cs.state_type in (CompoundStateType.CAMPAIGN_BATTLE, CompoundStateType.CAMPAIGN_BATTLE_DEFENDER)) else 0.0; offset += 1
    obs[offset] = 1.0 if (cs and cs.state_type == CompoundStateType.CAMPAIGN_SACRIFICE) else 0.0; offset += 1
    obs[offset] = 1.0 if (cs and cs.state_type == CompoundStateType.CITIZENSHIP_RESPONSE) else 0.0; offset += 1

    obs[offset] = gs.supply_spent_this_turn / 9.0; offset += 1
    obs[offset] = gs.actions_taken_this_turn / 10.0; offset += 1

    # Search cards in hand one-hot (3)
    if cs and cs.state_type == CompoundStateType.SEARCH_CHOOSE:
        for i in range(min(3, len(cs.cards_remaining))):
            obs[offset + i] = 1.0 if cs.cards_remaining[i] else 0.0
    offset += 3

    # Search source one-hot (2)
    if cs and cs.state_type == CompoundStateType.SEARCH_CHOOSE and cs.search_source:
        obs[offset] = 1.0 if cs.search_source == "deck" else 0.0
        obs[offset + 1] = 1.0 if cs.search_source == "discard" else 0.0
    offset += 2

    # Phase one-hot (2)
    if gs.phase == Phase.WAKE:
        obs[offset] = 1.0
    elif gs.phase == Phase.ACT:
        obs[offset + 1] = 1.0
    offset += 2

    assert offset - start == TURN_CONTEXT_SIZE, f"Turn context: {offset - start} != {TURN_CONTEXT_SIZE}"
    return offset


def _encode_win_proximity(gs: GameState, obs: np.ndarray, offset: int, player_index: int) -> int:
    """Encode win proximity features (30 floats)."""
    start = offset
    player = gs.players[player_index]

    total_faceup = sum(1 for s in gs.sites if s.is_faceup) or 1
    my_sites = gs.count_sites_ruled(player_index)
    obs[offset] = my_sites / total_faceup; offset += 1

    max_sites = max(gs.count_sites_ruled(i) for i in range(gs.num_players))
    obs[offset] = max_sites / total_faceup; offset += 1

    obs[offset] = 1.0 if gs.oathkeeper_holder == player_index else 0.0; offset += 1
    obs[offset] = 1.0 if (gs.oathkeeper_holder == player_index and
                           gs.oathkeeper_side == TitleSide.USURPER) else 0.0; offset += 1

    obs[offset] = 1.0 if player.revealed_vision is not None else 0.0; offset += 1

    from oath.engine.win_conditions import _check_vision_condition
    vision_met = False
    if player.revealed_vision is not None:
        vision_met = _check_vision_condition(gs, player_index, player.revealed_vision)
    obs[offset] = 1.0 if vision_met else 0.0; offset += 1

    obs[offset] = 1.0 if gs.visions_drawn >= 3 else 0.0; offset += 1

    from oath.engine.win_conditions import _check_successor_goal
    obs[offset] = 1.0 if (player.role == Role.CITIZEN and
                           _check_successor_goal(gs, player_index)) else 0.0; offset += 1

    obs[offset] = 1.0 if (gs.oathkeeper_holder == 0 and
                           gs.oathkeeper_side == TitleSide.OATHKEEPER) else 0.0; offset += 1
    obs[offset] = 1.0 if gs.oathkeeper_holder == 0 else 0.0; offset += 1

    # Threat levels (simplified)
    obs[offset] = 0.0; offset += 1  # nearest_opp_to_usurper_win
    obs[offset] = 0.0; offset += 1  # nearest_opp_to_vision_win

    # Advantages
    avg_favor = sum(p.favor for p in gs.players) / gs.num_players if gs.num_players > 0 else 0
    avg_secrets = sum(p.secrets for p in gs.players) / gs.num_players if gs.num_players > 0 else 0
    avg_warbands = sum(p.warbands_board for p in gs.players) / gs.num_players if gs.num_players > 0 else 0
    max_val = max(MAX_FAVOR_TOTAL, 1)

    obs[offset] = (player.favor - avg_favor) / max_val; offset += 1
    obs[offset] = (player.secrets - avg_secrets) / MAX_SECRETS_TOTAL; offset += 1
    obs[offset] = (player.warbands_board - avg_warbands) / MAX_WARBANDS_CHANCELLOR; offset += 1

    # Contested sites
    contested = 0
    for site in gs.sites:
        if site.is_faceup:
            pawns_at = sum(1 for p in gs.players if p.pawn_site == gs.sites.index(site))
            if pawns_at > 1:
                contested += 1
    obs[offset] = contested / MAX_SITES; offset += 1

    # Pawn colocated with (6)
    my_site = player.pawn_site
    for i in range(MAX_PLAYERS):
        if i < gs.num_players and i != player_index:
            rel_idx = _relative_index(i, player_index, gs.num_players)
            if rel_idx < 6:
                obs[offset + rel_idx] = 1.0 if gs.players[i].pawn_site == my_site else 0.0
    offset += 6

    obs[offset] = (MAX_ROUNDS - gs.round_number) / MAX_ROUNDS; offset += 1

    # Can win this turn (simplified)
    obs[offset] = 0.0; offset += 1

    # Reserved (6)
    offset += 6

    assert offset - start == WIN_PROXIMITY_SIZE, f"Win prox: {offset - start} != {WIN_PROXIMITY_SIZE}"
    return offset


def _encode_action_history(gs: GameState, obs: np.ndarray, offset: int, player_index: int) -> int:
    """Encode last 5 actions (5 × 40 = 200)."""
    history = gs.action_history[-5:] if gs.action_history else []

    for i in range(5):
        action_offset = offset + i * 40
        if i < len(history):
            record = history[len(history) - 1 - i]  # Most recent first

            # Acting player one-hot (6)
            rel_idx = _relative_index(record.player_index, player_index, gs.num_players)
            if rel_idx < MAX_PLAYERS:
                obs[action_offset + rel_idx] = 1.0

            # Action type one-hot (12)
            act_type = min(int(record.action_type), 11)
            obs[action_offset + 6 + act_type] = 1.0

            # Target site one-hot (8)
            if record.target_site is not None:
                obs[action_offset + 18 + record.target_site] = 1.0

            # Target player one-hot (6)
            if record.target_player is not None:
                t_rel = _relative_index(record.target_player, player_index, gs.num_players)
                if t_rel < MAX_PLAYERS:
                    obs[action_offset + 26 + t_rel] = 1.0

            obs[action_offset + 32] = 1.0 if record.was_successful else 0.0
            obs[action_offset + 33] = i / 4.0 if i < 5 else 1.0

    offset += ACTION_HISTORY_SIZE
    return offset


def _get_relative_player_order(gs: GameState, observer_idx: int) -> list[Optional[int]]:
    """Get player indices in relative order (excluding observer). Pad to 5."""
    others: list[Optional[int]] = []
    for i in range(1, MAX_PLAYERS):
        abs_idx = (observer_idx + i) % MAX_PLAYERS
        if abs_idx < gs.num_players:
            others.append(abs_idx)
        else:
            others.append(None)
    return others[:5]


def _relative_index(abs_idx: int, observer_idx: int, num_players: int) -> int:
    """Convert absolute player index to observer-relative index."""
    return (abs_idx - observer_idx) % max(num_players, MAX_PLAYERS)


def _extract_card_ids(gs: GameState, player_index: int) -> dict:
    """Extract integer card IDs for embedding lookup."""
    site_cards = []
    for site in gs.sites:
        for slot in range(MAX_CARDS_PER_SITE):
            card_id = site.cards[slot] if slot < len(site.cards) else 0
            site_cards.append(card_id or 0)

    self_advisers = []
    player = gs.players[player_index]
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot] if slot < len(player.advisers) else 0
        self_advisers.append(card_id or 0)

    return {
        "site_cards": np.array(site_cards, dtype=np.int32),
        "self_advisers": np.array(self_advisers, dtype=np.int32),
    }


# ── Chronicle Citizenship Observation ──────────────────────────────

CHRONICLE_OBS_SIZE = 51


def encode_chronicle_citizenship_observation(
    gs: GameState,
    player_index: int,
    new_oath_goal: int,
    new_successor_goal: int,
) -> np.ndarray:
    """Encode observation for chronicle citizenship decision.

    This special observation is used between games when an Exile
    must decide whether to accept citizenship. It encodes:
    1. New oath goal (one-hot, 4)
    2. New successor goal (one-hot, 4)
    3. Player's resources (6)
    4. Chancellor's resources (6)
    5. Resource comparison (4)
    6. Sites controlled by player and Chancellor (4)
    7. Banners held (4)
    8. World deck suit distribution hint (6)
    9. Relics held (2)
    10. Misc features (14)
    """
    from oath.enums import NUM_OATH_GOALS, NUM_SUCCESSOR_GOALS

    obs = np.zeros(CHRONICLE_OBS_SIZE, dtype=np.float32)
    offset = 0

    player = gs.players[player_index]
    chanc_idx = gs.chancellor_index
    chancellor = gs.players[chanc_idx]

    # New oath goal one-hot (4)
    obs[offset + new_oath_goal] = 1.0
    offset += NUM_OATH_GOALS

    # New successor goal one-hot (4)
    obs[offset + new_successor_goal] = 1.0
    offset += NUM_SUCCESSOR_GOALS

    # Player resources (6)
    obs[offset] = player.favor / MAX_FAVOR_TOTAL; offset += 1
    obs[offset] = player.secrets / MAX_SECRETS_TOTAL; offset += 1
    obs[offset] = player.warbands_board / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = player.warbands_bank / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = len(player.relics) / 6.0; offset += 1
    obs[offset] = gs.count_sites_ruled(player_index) / MAX_SITES; offset += 1

    # Chancellor resources (6)
    obs[offset] = chancellor.favor / MAX_FAVOR_TOTAL; offset += 1
    obs[offset] = chancellor.secrets / MAX_SECRETS_TOTAL; offset += 1
    obs[offset] = chancellor.warbands_board / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = chancellor.warbands_bank / MAX_WARBANDS_CHANCELLOR; offset += 1
    obs[offset] = len(chancellor.relics) / 6.0; offset += 1
    obs[offset] = gs.count_sites_ruled(chanc_idx) / MAX_SITES; offset += 1

    # Resource comparison: player - chancellor (4)
    obs[offset] = (player.favor - chancellor.favor) / MAX_FAVOR_TOTAL; offset += 1
    obs[offset] = (player.secrets - chancellor.secrets) / MAX_SECRETS_TOTAL; offset += 1
    my_sites = gs.count_sites_ruled(player_index)
    ch_sites = gs.count_sites_ruled(chanc_idx)
    obs[offset] = (my_sites - ch_sites) / MAX_SITES; offset += 1
    my_rb = len(player.relics)
    ch_rb = len(chancellor.relics)
    obs[offset] = (my_rb - ch_rb) / 6.0; offset += 1

    # Banners held (4)
    obs[offset] = 1.0 if gs.peoples_favor_holder == player_index else 0.0; offset += 1
    obs[offset] = 1.0 if gs.darkest_secret_holder == player_index else 0.0; offset += 1
    obs[offset] = 1.0 if gs.peoples_favor_holder == chanc_idx else 0.0; offset += 1
    obs[offset] = 1.0 if gs.darkest_secret_holder == chanc_idx else 0.0; offset += 1

    # World deck suit distribution hint (6)
    # Count suits of remaining world deck cards
    suit_counts = [0] * NUM_SUITS
    for card_id in gs.world_deck:
        card = get_card(card_id)
        if card.suit is not None:
            suit_counts[int(card.suit)] += 1
    total = max(sum(suit_counts), 1)
    for s in range(NUM_SUITS):
        obs[offset] = suit_counts[s] / total; offset += 1

    # Misc (fill remaining to CHRONICLE_OBS_SIZE)
    # Oathkeeper holder
    obs[offset] = 1.0 if gs.oathkeeper_holder == player_index else 0.0; offset += 1
    obs[offset] = 1.0 if gs.oathkeeper_holder == 0 else 0.0; offset += 1

    # Vision state
    obs[offset] = 1.0 if player.revealed_vision is not None else 0.0; offset += 1
    obs[offset] = gs.visions_drawn / MAX_VISIONS_DRAWN; offset += 1

    # Pad remaining
    while offset < CHRONICLE_OBS_SIZE:
        offset += 1

    return obs

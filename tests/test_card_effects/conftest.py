"""Shared fixtures for card effect tests."""

import pytest
from oath.engine.game import create_initial_state
from oath.enums import Phase, MAX_ADVISERS


@pytest.fixture
def gs():
    """Minimal game state for effect testing."""
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


@pytest.fixture
def setup_adviser():
    """Helper to place a card as a faceup adviser."""
    def _setup(gs, player_index, card_id, slot=0):
        gs.players[player_index].advisers[slot] = card_id
        gs.players[player_index].adviser_faceup[slot] = True
        return gs
    return _setup

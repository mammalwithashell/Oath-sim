"""Tests for observation tensor encoder."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.env.observation import encode_observation, OBS_SIZE
from oath.enums import Phase, NUM_ACTIONS


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


class TestObservationShape:
    def test_observation_shape(self, gs):
        result = encode_observation(gs, 0)
        assert result["observation"].shape == (OBS_SIZE,)
        assert result["action_mask"].shape == (NUM_ACTIONS,)

    def test_observation_dtype(self, gs):
        result = encode_observation(gs, 0)
        assert result["observation"].dtype == np.float32
        assert result["action_mask"].dtype == np.float32

    def test_observation_bounded(self, gs):
        result = encode_observation(gs, 0)
        obs = result["observation"]
        # Most values should be in [-1, 1] range
        assert np.all(obs >= -2.0), f"Min: {obs.min()}"
        assert np.all(obs <= 2.0), f"Max: {obs.max()}"

    def test_action_mask_binary(self, gs):
        result = encode_observation(gs, 0)
        mask = result["action_mask"]
        assert np.all((mask == 0.0) | (mask == 1.0))

    def test_action_mask_has_legal_actions(self, gs):
        result = encode_observation(gs, 0)
        mask = result["action_mask"]
        assert np.sum(mask) > 0, "Should have at least one legal action"


class TestPlayerRelativeObservation:
    def test_different_player_different_obs(self, gs):
        obs0 = encode_observation(gs, 0)["observation"]
        obs1 = encode_observation(gs, 1)["observation"]
        # Observations should differ (different player perspectives)
        assert not np.allclose(obs0, obs1)

    def test_self_always_first_in_encoding(self, gs):
        """The observing player's data should always be at the self-player offset."""
        from oath.env.observation import GLOBAL_SIZE, SITE_SIZE
        from oath.enums import MAX_SITES
        self_offset = GLOBAL_SIZE + SITE_SIZE * MAX_SITES
        obs0 = encode_observation(gs, 0)["observation"]
        obs1 = encode_observation(gs, 1)["observation"]
        # Both should have is_active=1 at the self-player section
        assert obs0[self_offset] == 1.0  # is_active for player 0 viewing
        assert obs1[self_offset] == 1.0  # is_active for player 1 viewing


class TestCardIDs:
    def test_card_ids_present(self, gs):
        result = encode_observation(gs, 0)
        assert "card_ids" in result
        assert "site_cards" in result["card_ids"]
        assert "self_advisers" in result["card_ids"]

    def test_card_ids_shape(self, gs):
        result = encode_observation(gs, 0)
        assert result["card_ids"]["site_cards"].shape == (24,)  # 8 sites × 3 cards
        assert result["card_ids"]["self_advisers"].shape == (3,)

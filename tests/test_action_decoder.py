"""Tests for action decoder."""

import pytest
import numpy as np

from oath.env.action_decoder import ActionDecoder, DecodedAction
from oath.engine.game import create_initial_state
from oath.enums import ActionType, Phase, NUM_ACTIONS


@pytest.fixture
def decoder():
    return ActionDecoder()


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


class TestDecodeAllActions:
    def test_all_action_ids_decode(self, decoder):
        """Every action ID (0–118) should decode without error."""
        for action_id in range(NUM_ACTIONS):
            decoded = decoder.decode(action_id)
            assert isinstance(decoded, DecodedAction)
            assert decoded.action_type is not None

    def test_invalid_action_id_raises(self, decoder):
        with pytest.raises(ValueError):
            decoder.decode(-1)
        with pytest.raises(ValueError):
            decoder.decode(NUM_ACTIONS)
        with pytest.raises(ValueError):
            decoder.decode(999)


class TestDecodeSpecific:
    def test_travel_actions(self, decoder):
        for i in range(8):
            decoded = decoder.decode(i)
            assert decoded.action_type == ActionType.TRAVEL
            assert decoded.site_index == i

    def test_search_actions(self, decoder):
        d = decoder.decode(8)
        assert d.action_type == ActionType.SEARCH
        assert d.search_destination == "deck"

        d = decoder.decode(9)
        assert d.action_type == ActionType.SEARCH
        assert d.search_destination == "discard"

    def test_muster_actions(self, decoder):
        for i in range(3):
            d = decoder.decode(10 + i)
            assert d.action_type == ActionType.MUSTER
            assert d.card_slot == i

    def test_campaign_declare(self, decoder):
        for i in range(5):
            d = decoder.decode(24 + i)
            assert d.action_type == ActionType.CAMPAIGN_DECLARE
            assert d.target_player == i + 1

    def test_search_play_encoding(self, decoder):
        # card[0] × dest[site] = action 66
        d = decoder.decode(66)
        assert d.action_type == ActionType.SEARCH_PLAY
        assert d.search_card_index == 0
        assert d.search_destination == "site"

        # card[0] × dest[adviser_up] = action 67
        d = decoder.decode(67)
        assert d.search_destination == "adviser_up"

        # card[1] × dest[site] = action 69
        d = decoder.decode(69)
        assert d.search_card_index == 1
        assert d.search_destination == "site"

    def test_sacrifice_count(self, decoder):
        for i in range(6):
            d = decoder.decode(60 + i)
            assert d.action_type == ActionType.CAMPAIGN_SACRIFICE
            assert d.sacrifice_count == i


class TestLegalMask:
    def test_mask_shape(self, decoder, gs):
        mask = decoder.get_legal_mask(gs, 0)
        assert mask.shape == (NUM_ACTIONS,)
        assert mask.dtype == np.float32

    def test_mask_has_legal_actions(self, decoder, gs):
        mask = decoder.get_legal_mask(gs, 0)
        assert np.sum(mask) > 0

    def test_end_act_always_legal(self, decoder, gs):
        mask = decoder.get_legal_mask(gs, 0)
        assert mask[43] == 1.0  # END_ACT_PHASE

    def test_mask_binary(self, decoder, gs):
        mask = decoder.get_legal_mask(gs, 0)
        assert np.all((mask == 0.0) | (mask == 1.0))

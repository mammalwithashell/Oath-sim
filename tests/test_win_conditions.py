"""Tests for win condition checks."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.engine.win_conditions import (
    check_usurper_win, check_vision_win, check_end_of_round_win,
    _check_vision_condition, _end_probability, _determine_winner,
)
from oath.enums import TitleSide, Role, OathGoal, Phase


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


class TestUsurperWin:
    def test_usurper_wins_on_next_turn(self, gs):
        gs.oathkeeper_holder = 1
        gs.oathkeeper_side = TitleSide.USURPER
        assert check_usurper_win(gs, 1)

    def test_non_usurper_does_not_win(self, gs):
        gs.oathkeeper_holder = 0
        gs.oathkeeper_side = TitleSide.OATHKEEPER
        assert not check_usurper_win(gs, 0)

    def test_wrong_player_does_not_win(self, gs):
        gs.oathkeeper_holder = 1
        gs.oathkeeper_side = TitleSide.USURPER
        assert not check_usurper_win(gs, 2)


class TestVisionWin:
    def test_vision_of_conquest(self, gs):
        gs.players[1].revealed_vision = 221
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 3
        # Player 1 needs most sites
        gs.sites[0].ruling_player = 1
        gs.sites[0].is_faceup = True
        gs.sites[1].ruling_player = None
        for i in range(2, 8):
            gs.sites[i].ruling_player = None

        assert check_vision_win(gs, 1)

    def test_vision_of_faith(self, gs):
        gs.players[1].revealed_vision = 222
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 3
        gs.darkest_secret_holder = 1
        assert check_vision_win(gs, 1)

    def test_vision_of_rebellion(self, gs):
        gs.players[1].revealed_vision = 223
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 3
        gs.peoples_favor_holder = 1
        assert check_vision_win(gs, 1)

    def test_vision_requires_enough_drawn(self, gs):
        gs.players[1].revealed_vision = 222
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 2  # Not enough
        gs.darkest_secret_holder = 1
        assert not check_vision_win(gs, 1)

    def test_chancellor_cannot_vision_win(self, gs):
        gs.players[0].revealed_vision = 222
        gs.players[0].role = Role.CHANCELLOR
        gs.visions_drawn = 3
        gs.darkest_secret_holder = 0
        assert not check_vision_win(gs, 0)


class TestEndOfRound:
    def test_no_end_before_round_5(self, gs):
        gs.round_number = 3
        assert check_end_of_round_win(gs) is None

    def test_round_8_always_ends(self, gs):
        gs.round_number = 8
        result = check_end_of_round_win(gs)
        assert result is not None

    def test_end_probability_increases(self):
        assert _end_probability(4) == 0.0
        assert _end_probability(5) == pytest.approx(1 / 6)
        assert _end_probability(6) == pytest.approx(2 / 6)
        assert _end_probability(7) == pytest.approx(4 / 6)
        assert _end_probability(8) == 1.0


class TestDetermineWinner:
    def test_oathkeeper_wins_by_default(self, gs):
        gs.oathkeeper_holder = 0
        winner = _determine_winner(gs)
        assert winner == 0

    def test_vision_holder_can_win(self, gs):
        gs.players[1].revealed_vision = 222
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 3
        gs.darkest_secret_holder = 1
        winner = _determine_winner(gs)
        assert winner == 1

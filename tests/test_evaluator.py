"""Tests for the chronicle evaluation infrastructure."""

import pytest

from oath.enums import OathGoal, Role, WinType
from oath.engine.game import create_initial_state
from oath.engine.win_conditions import (
    check_start_of_turn_wins, _determine_winner,
)
from oath.evaluation.evaluator import (
    ChronicleEvaluator, ChronicleResult, GameResult,
)
from oath.agents.random_agent import RandomAgent
from oath.state.chronicle_state import ChronicleState


class TestWinType:
    """Test that WinType is correctly set in win determination."""

    def test_oathkeeper_default_win_type(self):
        """Oathkeeper default should set OATHKEEPER_DEFAULT."""
        gs = create_initial_state(num_players=4, seed=1)
        # Player 0 is Chancellor and Oathkeeper by default
        winner = _determine_winner(gs)
        assert winner == 0
        assert gs.win_type == WinType.OATHKEEPER_DEFAULT

    def test_usurper_win_type(self):
        """Usurper win should set USURPER."""
        from oath.enums import TitleSide
        gs = create_initial_state(num_players=4, seed=1)
        # Give player 1 the Usurper title
        gs.oathkeeper_holder = 1
        gs.oathkeeper_side = TitleSide.USURPER
        winner = check_start_of_turn_wins(gs, 1)
        assert winner == 1
        assert gs.win_type == WinType.USURPER


class TestChancellorIndex:
    """Test the chancellor_index property."""

    def test_default_chancellor_is_player_0(self):
        gs = create_initial_state(num_players=4, seed=1)
        assert gs.chancellor_index == 0

    def test_chancellor_rotation_via_chronicle(self):
        """When chronicle.last_winner is set, that player becomes Chancellor."""
        cs = ChronicleState()
        cs.last_winner = 2
        gs = create_initial_state(num_players=4, seed=1, chronicle=cs)
        assert gs.chancellor_index == 2
        assert gs.players[2].role == Role.CHANCELLOR
        # Other players should be Exile
        assert gs.players[0].role == Role.EXILE
        assert gs.players[1].role == Role.EXILE
        assert gs.players[3].role == Role.EXILE

    def test_turn_order_starts_with_chancellor(self):
        """Turn order should start with the Chancellor."""
        cs = ChronicleState()
        cs.last_winner = 2
        gs = create_initial_state(num_players=4, seed=1, chronicle=cs)
        assert gs.turn_order[0] == 2
        assert gs.current_player_index == 2

    def test_chancellor_gets_oathkeeper(self):
        """Chancellor (wherever seated) should start with Oathkeeper."""
        cs = ChronicleState()
        cs.last_winner = 3
        gs = create_initial_state(num_players=4, seed=1, chronicle=cs)
        assert gs.oathkeeper_holder == 3

    def test_chancellor_gets_more_warbands(self):
        """Chancellor gets 24 warbands, exiles get 14."""
        cs = ChronicleState()
        cs.last_winner = 1
        gs = create_initial_state(num_players=4, seed=1, chronicle=cs)
        chanc = gs.players[1]
        assert chanc.role == Role.CHANCELLOR
        # Chancellor total warbands = 24
        assert chanc.warbands_bank + chanc.warbands_board == 24


@pytest.mark.timeout(60)
class TestChronicleEvaluator:
    """Test the ChronicleEvaluator end-to-end."""

    def test_short_chronicle_completes(self):
        """A 3-game chronicle with random agents should complete."""
        evaluator = ChronicleEvaluator(
            num_players=4,
            num_games=3,
            seed=42,
            max_iter_per_game=3000,
        )
        result = evaluator.run()
        assert len(result.games) == 3
        for g in result.games:
            assert g.winner is not None
            assert g.win_type is not None

    def test_game_result_fields(self):
        """GameResult should have all fields populated."""
        evaluator = ChronicleEvaluator(
            num_players=4,
            num_games=1,
            seed=99,
            max_iter_per_game=3000,
        )
        result = evaluator.run()
        g = result.games[0]
        assert g.game_index == 0
        assert 0 <= g.winner < 4
        assert g.win_type in list(WinType)
        assert g.winner_role in list(Role)
        assert g.oath_goal in list(OathGoal)
        assert g.round_number >= 1
        assert len(g.roles) == 4
        assert len(g.sites_ruled) == 4

    def test_chronicle_result_properties(self):
        """ChronicleResult computed properties should work."""
        evaluator = ChronicleEvaluator(
            num_players=4,
            num_games=3,
            seed=77,
            max_iter_per_game=3000,
        )
        result = evaluator.run()
        assert sum(result.win_counts.values()) == 3
        assert sum(result.win_type_counts.values()) == 3
        assert len(result.oath_goal_sequence) == 3
        assert result.avg_game_length > 0

    def test_summarize_output(self):
        """summarize() should return a non-empty string."""
        evaluator = ChronicleEvaluator(
            num_players=4,
            num_games=2,
            seed=55,
            max_iter_per_game=3000,
        )
        result = evaluator.run()
        summary = ChronicleEvaluator.summarize(result)
        assert len(summary) > 0
        assert "Chronicle Summary" in summary
        assert "Win Counts" in summary

    def test_different_seeds_give_different_results(self):
        """Different seeds should generally produce different outcomes."""
        results = []
        for seed in [10, 20]:
            evaluator = ChronicleEvaluator(
                num_players=4,
                num_games=3,
                seed=seed,
                max_iter_per_game=3000,
            )
            results.append(evaluator.run())
        # At least one game should differ in winner or win_type
        any_diff = False
        for i in range(3):
            if (results[0].games[i].winner != results[1].games[i].winner or
                    results[0].games[i].win_type != results[1].games[i].win_type):
                any_diff = True
                break
        assert any_diff, "Different seeds produced identical results"

    def test_agent_configs_recorded(self):
        """Agent configurations should be recorded in result."""
        agents = {1: RandomAgent(seed=1)}
        evaluator = ChronicleEvaluator(
            num_players=4,
            num_games=1,
            agents=agents,
            seed=42,
            max_iter_per_game=3000,
        )
        result = evaluator.run()
        assert "RandomAgent" in result.agent_configs.values()

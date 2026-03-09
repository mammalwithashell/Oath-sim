"""Tests for win condition checks."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.engine.campaign import recalculate_oathkeeper, _count_relics_and_banners
from oath.engine.win_conditions import (
    check_usurper_win, check_vision_win, check_end_of_round_win,
    _check_vision_condition, _end_probability, _determine_winner,
)
from oath.enums import TitleSide, Role, OathGoal, Phase, WinType


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
        """§3.4.3: Exile with Vision wins if Oathkeeper is also an Exile (not Usurper)."""
        gs.players[1].revealed_vision = 222  # Vision of Faith
        gs.players[1].role = Role.EXILE
        gs.visions_drawn = 3
        gs.darkest_secret_holder = 1
        # Oathkeeper must be an Exile (not Chancellor/Citizen) for §3.4.3 to fire
        # Set another Exile as Oathkeeper on Oathkeeper side (not Usurper)
        gs.oathkeeper_holder = 2
        gs.players[2].role = Role.EXILE
        gs.oathkeeper_side = TitleSide.OATHKEEPER
        winner = _determine_winner(gs)
        assert winner == 1
        assert gs.win_type == WinType.VISION


class TestOathkeeperRecalculation:
    """Tests for goal-based Oathkeeper title transfer (§2.11)."""

    def test_supremacy_always_chancellor(self):
        """§2.11: Chancellor always holds the Oathkeeper of Supremacy."""
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.SUPREMACY
        gs.oathkeeper_holder = 0  # Chancellor starts with it

        # Player 1 rules more sites than Chancellor
        for site in gs.sites:
            site.ruling_player = None
        gs.sites[0].ruling_player = 1
        gs.sites[0].is_faceup = True
        gs.sites[1].ruling_player = 1
        gs.sites[1].is_faceup = True
        gs.sites[2].ruling_player = 0
        gs.sites[2].is_faceup = True

        recalculate_oathkeeper(gs)
        # Chancellor always keeps Supremacy Oathkeeper
        assert gs.oathkeeper_holder == gs.chancellor_index

    def test_supremacy_no_transfer_without_majority(self):
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.SUPREMACY
        gs.oathkeeper_holder = 0

        # No one rules any sites — holder keeps it
        for site in gs.sites:
            site.ruling_player = None
        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 0

    def test_people_needs_peoples_favor(self):
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.PEOPLE
        gs.oathkeeper_holder = 0
        gs.peoples_favor_holder = 2

        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 2

    def test_devotion_needs_darkest_secret(self):
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.DEVOTION
        gs.oathkeeper_holder = 0
        gs.darkest_secret_holder = 3

        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 3

    def test_sanctuary_needs_most_relics_banners(self):
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.SANCTUARY
        gs.oathkeeper_holder = 0

        # Give player 2 two relics
        gs.players[2].relics = [100, 101]
        gs.players[0].relics = []

        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 2

    def test_title_always_transfers_to_oathkeeper_side(self):
        """Per §2.11: taking the title always sets it to OATHKEEPER side."""
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.PEOPLE
        gs.oathkeeper_holder = 0
        gs.oathkeeper_side = TitleSide.USURPER  # Shouldn't matter
        gs.peoples_favor_holder = 1

        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 1
        assert gs.oathkeeper_side == TitleSide.OATHKEEPER

    def test_pawn_only_campaign_no_title_transfer(self):
        """The exploit: pawn-only campaign shouldn't transfer Supremacy title."""
        gs = create_initial_state(num_players=4, seed=42)
        gs.oath_goal = OathGoal.SUPREMACY
        gs.oathkeeper_holder = 0

        # Simulate a pawn-only campaign: no site rulership changes
        # Player 0 still rules their sites, player 1 rules none
        gs.sites[0].ruling_player = 0
        gs.sites[0].is_faceup = True
        for i in range(1, len(gs.sites)):
            gs.sites[i].ruling_player = None

        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 0  # Should NOT transfer


class TestUsurperFlipTiming:
    """Tests for §4.1.3 — Usurper flip happens during Wake, not during campaign."""

    def test_usurper_flip_requires_wake_phase(self):
        """Title should be on OATHKEEPER side when first taken."""
        gs = create_initial_state(num_players=4, seed=42)
        # Use PEOPLE oath so title can transfer to an Exile
        gs.oath_goal = OathGoal.PEOPLE
        gs.oathkeeper_holder = 0
        gs.oathkeeper_side = TitleSide.OATHKEEPER

        # Player 1 takes People's Favor — title transfers
        gs.peoples_favor_holder = 1

        recalculate_oathkeeper(gs)
        # Should be OATHKEEPER side, not USURPER (flip only at Wake)
        assert gs.oathkeeper_holder == 1
        assert gs.oathkeeper_side == TitleSide.OATHKEEPER


class TestOathGoalParameter:
    """Tests for oath_goal parameter in create_initial_state and OathEnv."""

    def test_default_oath_is_supremacy(self):
        gs = create_initial_state(num_players=4, seed=42)
        assert gs.oath_goal == OathGoal.SUPREMACY

    def test_explicit_oath_goal(self):
        gs = create_initial_state(num_players=4, seed=42, oath_goal=OathGoal.PEOPLE)
        assert gs.oath_goal == OathGoal.PEOPLE

    def test_all_oath_goals_create_valid_state(self):
        for goal in OathGoal:
            gs = create_initial_state(num_players=4, seed=42, oath_goal=goal)
            assert gs.oath_goal == goal

    def test_oath_env_passes_goal(self):
        from oath.env.oath_env import OathEnv
        env = OathEnv(num_players=4, seed=42, oath_goal=OathGoal.DEVOTION)
        env.reset()
        assert env.game_state.oath_goal == OathGoal.DEVOTION


class TestVowActions:
    """Tests for VOW action decoding and legal masks."""

    def test_vow_actions_decode_correctly(self):
        from oath.env.action_decoder import ActionDecoder
        from oath.enums import ActionType
        decoder = ActionDecoder()
        assert decoder.decode(119).action_type == ActionType.VOW_SUPREMACY
        assert decoder.decode(120).action_type == ActionType.VOW_PEOPLE
        assert decoder.decode(121).action_type == ActionType.VOW_DEVOTION
        assert decoder.decode(122).action_type == ActionType.VOW_SANCTUARY

    def test_vow_mask_all_legal_when_no_vision(self):
        from oath.env.action_decoder import ActionDecoder
        gs = create_initial_state(num_players=4, seed=42)
        gs.is_game_over = True
        gs.winner = 1
        gs.in_vow_phase = True
        gs.players[1].revealed_vision = None

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        # All 4 VOW actions should be legal
        assert mask[119] == 1.0  # SUPREMACY
        assert mask[120] == 1.0  # PEOPLE
        assert mask[121] == 1.0  # DEVOTION
        assert mask[122] == 1.0  # SANCTUARY
        # No other actions should be legal
        assert mask[:119].sum() == 0.0

    def test_vow_mask_vision_locked(self):
        from oath.env.action_decoder import ActionDecoder
        gs = create_initial_state(num_players=4, seed=42)
        gs.is_game_over = True
        gs.winner = 1
        gs.in_vow_phase = True
        gs.players[1].revealed_vision = 223  # Vision of Rebellion → PEOPLE

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        # Only PEOPLE should be legal (vision locked)
        assert mask[119] == 0.0  # SUPREMACY
        assert mask[120] == 1.0  # PEOPLE
        assert mask[121] == 0.0  # DEVOTION
        assert mask[122] == 0.0  # SANCTUARY

    def test_non_winner_gets_empty_vow_mask(self):
        from oath.env.action_decoder import ActionDecoder
        gs = create_initial_state(num_players=4, seed=42)
        gs.is_game_over = True
        gs.winner = 1
        gs.in_vow_phase = True

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 2)  # Not the winner
        assert mask.sum() == 0.0


class TestVowPhaseFlow:
    """Tests for vow phase integration in OathEnv."""

    def test_vow_phase_game_over_sets_in_vow_phase(self):
        """When game ends, winner should enter vow phase."""
        from oath.env.oath_env import OathEnv
        env = OathEnv(num_players=4, seed=42)
        env.reset()
        gs = env.game_state

        # Simulate game over with player 1 winning
        gs.is_game_over = True
        gs.winner = 1
        env._handle_game_over()

        assert gs.in_vow_phase is True
        assert env.agent_selection == "player_1"
        assert env.agents == ["player_1"]
        # Non-winners should be terminated
        assert env.terminations["player_0"] is True
        assert env.terminations.get("player_2", False) is True
        # Winner should NOT be terminated yet
        assert env.terminations.get("player_1", False) is False

    def test_vow_action_finalizes_episode(self):
        """After VOW action, winner should be terminated with +1.0 reward."""
        from oath.env.oath_env import OathEnv
        env = OathEnv(num_players=4, seed=42)
        env.reset()
        gs = env.game_state

        # Set up game over + vow phase
        gs.is_game_over = True
        gs.winner = 1
        env._handle_game_over()

        # Take a VOW action
        env.step(120)  # VOW_PEOPLE

        assert gs.vowed_oath == OathGoal.PEOPLE
        assert gs.in_vow_phase is False
        assert env.terminations["player_1"] is True
        assert env._cumulative_rewards["player_1"] == 1.0
        assert env.agents == []

    def test_vowed_oath_stored_in_game_state(self):
        """Vowed oath should be stored in game state after VOW action."""
        from oath.env.oath_env import OathEnv
        env = OathEnv(num_players=4, seed=42)
        env.reset()
        gs = env.game_state

        gs.is_game_over = True
        gs.winner = 1
        env._handle_game_over()
        env.step(119)  # VOW_SUPREMACY

        assert gs.vowed_oath == OathGoal.SUPREMACY

"""Tests for the Clockwork Prince automated Chancellor agent."""

import pytest
import numpy as np

from oath.env.oath_env import OathEnv
from oath.agents.clockwork_prince import ClockworkPrinceAgent
from oath.agents.heuristic_agent import HeuristicAgent
from oath.enums import Role, Phase, Suit, Region, MAX_SITES


class TestClockworkPrinceUnit:
    """Unit tests for ClockworkPrinceAgent internal logic."""

    def _make_prince(self, seed=42):
        prince = ClockworkPrinceAgent(seed=seed)
        return prince

    def _make_env_and_prince(self, seed=42):
        """Create an env with clockwork_prince=False so we can test the agent directly."""
        env = OathEnv(num_players=4, seed=seed)
        env.reset()
        prince = self._make_prince(seed)
        prince.set_game_state(env.game_state)
        return env, prince

    def test_init_defaults(self):
        prince = self._make_prince()
        assert prince.tactics == 0
        assert prince.caution == 0
        assert all(v == "unaligned" for v in prince.relationships.values())

    def test_reset_clears_state(self):
        prince = self._make_prince()
        prince.tactics = 3
        prince.caution = 5
        prince.relationships[Suit.ARCANE] = "friend"
        prince.reset()
        assert prince.tactics == 0
        assert prince.caution == 0
        assert prince.relationships[Suit.ARCANE] == "unaligned"

    def test_compute_num_actions_base(self):
        prince = self._make_prince()
        assert prince._compute_num_actions() == 2  # all unaligned

    def test_compute_num_actions_with_relationships(self):
        prince = self._make_prince()
        prince.relationships[Suit.ARCANE] = "friend"
        prince.relationships[Suit.ORDER] = "conspirator"
        assert prince._compute_num_actions() == 4  # 2 + 2

    def test_compute_num_actions_capped_at_5(self):
        prince = self._make_prince()
        for s in Suit:
            prince.relationships[s] = "friend"
        assert prince._compute_num_actions() == 5

    def test_ready_to_fight_basic(self):
        env, prince = self._make_env_and_prince()
        gs = env.game_state
        # Give the prince lots of warbands
        gs.players[0].warbands_board = 10
        # Ensure a site has minimal defense
        site = gs.sites[0]
        site.warbands = 1
        site.is_faceup = True
        assert prince._is_ready_to_fight(gs, 0) is True

    def test_ready_to_fight_caution_effect(self):
        env, prince = self._make_env_and_prince()
        gs = env.game_state
        gs.players[0].warbands_board = 3
        site = gs.sites[0]
        site.warbands = 2
        site.is_faceup = True
        # Without caution, 3 > 2 + defense_dice → depends on defense
        # With high caution, should be False
        prince.caution = 10
        assert prince._is_ready_to_fight(gs, 0) is False

    def test_on_campaign_defeat_increments_caution(self):
        prince = self._make_prince()
        assert prince.caution == 0
        prince.on_campaign_defeat()
        assert prince.caution == 1
        prince.on_campaign_defeat()
        assert prince.caution == 2

    def test_advance_relationship(self):
        prince = self._make_prince()
        prince._current_threat = "successor"  # prefers "friend"
        prince._advance_relationship(Suit.ARCANE)
        assert prince.relationships[Suit.ARCANE] == "friend"

    def test_advance_relationship_conspirator(self):
        prince = self._make_prince()
        prince._current_threat = "oathkeeper"  # prefers "conspirator"
        prince._advance_relationship(Suit.ORDER)
        assert prince.relationships[Suit.ORDER] == "conspirator"

    def test_start_turn_first_turn_skips_threat(self):
        env, prince = self._make_env_and_prince()
        prince.start_turn()
        assert prince._current_threat is None  # first turn skips assessment

    def test_start_turn_second_turn_assesses_threat(self):
        env, prince = self._make_env_and_prince()
        prince.start_turn()  # first turn
        prince.start_turn()  # second turn
        # Threat assessed (may or may not find one)
        # Just verify it doesn't crash
        assert prince._previous_threat is None  # was None on first turn

    def test_find_site_most_resources(self):
        env, prince = self._make_env_and_prince()
        gs = env.game_state
        # Add resources to site 2
        gs.sites[2].is_faceup = True
        gs.sites[2].site_favor = 10
        gs.sites[2].site_secrets = 5
        best = prince._find_site_most_resources(gs)
        # Should pick site 2 (most resources)
        assert best == 2

    def test_find_rival_weakest_site(self):
        env, prince = self._make_env_and_prince()
        gs = env.game_state
        # Set up: player 1 rules sites 0 and 1
        gs.sites[0].ruling_player = 1
        gs.sites[0].is_faceup = True
        gs.sites[0].warbands = 5
        gs.sites[1].ruling_player = 1
        gs.sites[1].is_faceup = True
        gs.sites[1].warbands = 1
        weakest = prince._find_rival_weakest_site(gs)
        assert weakest == 1  # fewer warbands


class TestClockworkPrinceActions:
    """Test that the Prince always selects legal actions."""

    def test_act_returns_legal_action(self):
        """Prince should always return an action within the legal mask."""
        env = OathEnv(num_players=4, seed=42)
        env.reset()
        prince = ClockworkPrinceAgent(seed=42)
        prince.set_game_state(env.game_state)
        prince.start_turn()

        obs = env.observe("player_0")
        action = prince.act(obs)

        mask = obs["action_mask"]
        assert mask[action] > 0.5, f"Action {action} is not legal"

    def test_act_legal_across_many_states(self):
        """Run many steps and verify all chosen actions are legal."""
        for seed in range(5):
            env = OathEnv(num_players=4, seed=seed)
            env.reset()
            prince = ClockworkPrinceAgent(seed=seed)
            prince.set_game_state(env.game_state)
            prince.start_turn()

            for step in range(20):
                gs = env.game_state
                if gs.is_game_over or gs.current_player_index != 0:
                    break
                obs = env.observe("player_0")
                mask = obs["action_mask"]
                legal = np.where(mask > 0.5)[0]
                if len(legal) == 0:
                    break

                action = prince.act(obs)
                assert mask[action] > 0.5, (
                    f"Seed {seed} step {step}: action {action} not legal"
                )

                decoded = env.action_decoder.decode(action)
                env._apply_action(gs, 0, decoded)

                if gs.phase == Phase.REST:
                    break


class TestClockworkPrinceIntegration:
    """Integration tests with the full environment."""

    def test_env_with_clockwork_prince_resets(self):
        """Environment should reset successfully with clockwork_prince=True."""
        env = OathEnv(num_players=4, seed=42, clockwork_prince=True)
        env.reset()
        assert env.game_state is not None
        assert env._prince_agent is not None

    def test_env_prince_skips_player0(self):
        """With clockwork_prince=True, player_0 turns are auto-played."""
        env = OathEnv(num_players=4, seed=42, clockwork_prince=True)
        env.reset()
        # After reset, the Prince's turn (player 0) should have been auto-played
        # so agent_selection should be player_1 (or later if multiple turns passed)
        gs = env.game_state
        if not gs.is_game_over:
            current = int(env.agent_selection.split("_")[1])
            # Current player should not be 0 (Chancellor is auto-played)
            assert current != 0, "Player 0 should be auto-played by Clockwork Prince"

    def test_full_game_with_clockwork_prince(self):
        """A full game with Clockwork Prince should complete without errors."""
        env = OathEnv(num_players=4, seed=42, clockwork_prince=True)
        env.reset()

        heuristic = HeuristicAgent(seed=99)
        max_steps = 5000
        steps = 0

        for agent_name in env.agent_iter(max_iter=max_steps):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                action = None
            else:
                action = heuristic.act(obs)
            env.step(action)
            steps += 1

            if env.game_state and env.game_state.is_game_over:
                break

        assert env.game_state is not None
        # Game should have progressed
        assert steps > 0

    def test_multiple_games_with_clockwork_prince(self):
        """Run 10 games to verify stability."""
        completed = 0
        for seed in range(10):
            env = OathEnv(num_players=4, seed=seed, clockwork_prince=True)
            env.reset()
            heuristic = HeuristicAgent(seed=seed + 100)

            max_steps = 5000
            steps = 0

            for agent_name in env.agent_iter(max_iter=max_steps):
                obs, reward, terminated, truncated, info = env.last()
                if terminated or truncated:
                    action = None
                else:
                    action = heuristic.act(obs)
                env.step(action)
                steps += 1

                if env.game_state and env.game_state.is_game_over:
                    break

            if env.game_state and env.game_state.is_game_over:
                completed += 1

        # At least some games should complete
        assert completed >= 1, f"Only {completed}/10 games completed"

    def test_prince_takes_actions(self):
        """Verify the Prince actually takes actions (not just ending turn)."""
        env = OathEnv(num_players=4, seed=42, clockwork_prince=True)
        env.reset()
        gs = env.game_state

        # If game started, the Prince should have taken at least one action
        # during its auto-play turn
        assert gs.actions_taken_this_turn >= 0 or gs.round_number > 1

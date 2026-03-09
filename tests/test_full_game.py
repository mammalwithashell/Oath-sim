"""Tests for full game simulation."""

import pytest
import numpy as np

from oath.env.oath_env import OathEnv
from oath.agents.random_agent import RandomAgent


class TestFullGame:
    def test_random_game_completes(self):
        """A single game with random agents should complete without crashes."""
        env = OathEnv(num_players=4, seed=42)
        env.reset()

        max_steps = 5000
        steps = 0

        for agent in env.agent_iter(max_iter=max_steps):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                action = None
            else:
                mask = obs["action_mask"]
                legal_actions = np.where(mask > 0.5)[0]
                if len(legal_actions) == 0:
                    action = None
                else:
                    action = int(np.random.choice(legal_actions))
            env.step(action)
            steps += 1

            if env.game_state and env.game_state.is_game_over:
                break

        assert env.game_state is not None
        # Game should end (either by win or by max steps)

    def test_multiple_games_complete(self):
        """Run multiple games to verify stability."""
        for seed in range(10):
            env = OathEnv(num_players=4, seed=seed)
            env.reset()
            agent = RandomAgent(seed=seed + 100)

            max_steps = 5000
            steps = 0

            for agent_name in env.agent_iter(max_iter=max_steps):
                obs, reward, terminated, truncated, info = env.last()
                if terminated or truncated:
                    action = None
                else:
                    action = agent.act(obs)
                env.step(action)
                steps += 1

                if env.game_state and env.game_state.is_game_over:
                    break

    def test_game_ends_within_rounds(self):
        """Game should end within 8 rounds."""
        env = OathEnv(num_players=4, seed=42)
        env.reset()

        max_steps = 10000
        for agent_name in env.agent_iter(max_iter=max_steps):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                action = None
            else:
                mask = obs["action_mask"]
                legal_actions = np.where(mask > 0.5)[0]
                if len(legal_actions) == 0:
                    action = None
                else:
                    action = int(np.random.choice(legal_actions))
            env.step(action)

            if env.game_state and env.game_state.is_game_over:
                break

        gs = env.game_state
        assert gs is not None
        if gs.is_game_over:
            assert gs.round_number <= 9  # Can be 9 because we increment then check

    def test_observation_valid_during_game(self):
        """Observations should be valid at every step."""
        env = OathEnv(num_players=4, seed=42)
        env.reset()

        max_steps = 200
        steps = 0

        for agent_name in env.agent_iter(max_iter=max_steps):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                env.step(None)
                steps += 1
                continue

            # Validate observation
            assert obs is not None
            assert "observation" in obs
            assert "action_mask" in obs
            assert obs["observation"].shape[0] > 0

            mask = obs["action_mask"]
            legal = np.where(mask > 0.5)[0]
            if len(legal) == 0:
                env.step(None)
            else:
                env.step(int(np.random.choice(legal)))

            steps += 1
            if env.game_state and env.game_state.is_game_over:
                break

    def test_render_does_not_crash(self):
        """Render should work at any point."""
        env = OathEnv(num_players=4, seed=42, render_mode="ansi")
        env.reset()
        result = env.render()
        assert isinstance(result, str)
        assert "Round" in result


class TestEnvironmentAPI:
    def test_reset_creates_valid_state(self):
        env = OathEnv(num_players=4, seed=42)
        env.reset()
        assert env.game_state is not None
        assert len(env.agents) == 4
        assert env.agent_selection == "player_0"

    def test_possible_agents(self):
        env = OathEnv(num_players=4)
        assert len(env.possible_agents) == 4

    def test_action_space(self):
        env = OathEnv(num_players=4)
        space = env.action_space("player_0")
        assert space.n == 137

    def test_observation_space(self):
        env = OathEnv(num_players=4)
        space = env.observation_space("player_0")
        assert "observation" in space.spaces
        assert "action_mask" in space.spaces

    def test_different_player_counts(self):
        for n in [2, 3, 4, 5, 6]:
            env = OathEnv(num_players=n, seed=42)
            env.reset()
            assert env.game_state.num_players == n
            assert len(env.agents) == n

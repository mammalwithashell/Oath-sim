"""Train an RL agent for Oath using MaskablePPO (sb3-contrib).

Uses a single-agent wrapper where the RL agent plays as one exile,
other exiles use a heuristic agent, and the Chancellor is played by
the Clockwork Prince automa.

Usage:
    # Train against heuristic opponents (default)
    python scripts/train_agent.py

    # Train against random opponents first (easier)
    python scripts/train_agent.py --opponent random --timesteps 500000

    # Resume training from checkpoint
    python scripts/train_agent.py --resume models/oath_exile_latest.zip

    # Customize training
    python scripts/train_agent.py --timesteps 2000000 --n-envs 8 --seed 42
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
from gymnasium import spaces, Env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import (
    BaseCallback, CheckpointCallback, CallbackList,
)
from stable_baselines3.common.utils import set_random_seed
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oath.env.oath_env import OathEnv
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent


class OathSingleAgentWrapper(Env):
    """Wraps Oath's multi-agent env for single-agent RL training.

    The RL agent controls one exile player. Other exiles use a fill agent
    (random or heuristic). Chancellor is played by the Clockwork Prince.
    """

    def __init__(self, player_id=1, opponent="heuristic", seed=None):
        super().__init__()
        self.player_id = player_id
        self.player_name = f"player_{player_id}"
        self._seed = seed
        self._opponent_type = opponent

        self._env = OathEnv(num_players=4, clockwork_prince=True, seed=seed)
        self._fill_agent = self._make_fill_agent(opponent, seed)

        obs_space = self._env.observation_space(self.player_name)
        self.observation_space = spaces.Dict({
            "observation": obs_space["observation"],
            "action_mask": obs_space["action_mask"],
        })
        self.action_space = self._env.action_space(self.player_name)

        self._episode_reward = 0.0
        self._episode_length = 0
        self._wins = 0
        self._games = 0

    @staticmethod
    def _make_fill_agent(opponent, seed):
        if opponent == "random":
            return RandomAgent(seed=seed)
        return HeuristicAgent(seed=seed)

    def reset(self, seed=None, options=None):
        self._env.reset(seed=seed)
        self._advance_to_player()
        obs = self._get_obs()
        self._episode_reward = 0.0
        self._episode_length = 0
        return obs, {}

    def step(self, action):
        self._env.step(int(action))
        self._advance_to_player()

        obs = self._get_obs()
        reward = self._env._cumulative_rewards.get(self.player_name, 0.0)
        # Reset cumulative so we get per-step rewards
        self._env._cumulative_rewards[self.player_name] = 0.0

        term = self._env.terminations.get(self.player_name, False)
        trunc = self._env.truncations.get(self.player_name, False)
        info = {}

        self._episode_reward += reward
        self._episode_length += 1

        if term or trunc:
            self._games += 1
            won = (self._env.game_state is not None and
                   self._env.game_state.winner == self.player_id)
            if won:
                self._wins += 1
            info["episode"] = {
                "r": self._episode_reward,
                "l": self._episode_length,
                "won": won,
            }

        return obs, reward, term, trunc, info

    def _get_obs(self):
        if not self._env.agents:
            # Game over — return dummy obs
            return {
                "observation": np.zeros(
                    self.observation_space["observation"].shape,
                    dtype=np.float32,
                ),
                "action_mask": np.ones(
                    self.observation_space["action_mask"].shape,
                    dtype=np.int8,
                ),
            }
        return self._env.observe(self.player_name)

    def _advance_to_player(self):
        """Step other agents until it's our turn or game is over."""
        for _ in range(1000):
            if not self._env.agents:
                break
            if self._env.agent_selection == self.player_name:
                break
            obs, _, term, trunc, _ = self._env.last()
            if term or trunc:
                self._env.step(None)
            else:
                action = self._fill_agent.act(obs)
                self._env.step(action)

    def action_masks(self):
        """Return current action mask for MaskablePPO."""
        obs = self._get_obs()
        return np.array(obs["action_mask"], dtype=bool)


def mask_fn(env):
    """Extract action mask from the wrapped environment."""
    return env.action_masks()


class WinRateCallback(BaseCallback):
    """Logs win rate over a rolling window."""

    def __init__(self, window=100, verbose=1):
        super().__init__(verbose)
        self.window = window
        self.results = []
        self._last_log_time = 0

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            ep = info.get("episode")
            if ep:
                self.results.append(ep["won"])

        # Log every 30 seconds
        now = time.time()
        if now - self._last_log_time > 30 and len(self.results) >= 10:
            recent = self.results[-self.window:]
            wr = sum(recent) / len(recent) * 100
            total = len(self.results)
            if self.verbose:
                print(
                    f"  [WinRate] {total} games | "
                    f"last {len(recent)}: {wr:.1f}% wins | "
                    f"timesteps: {self.num_timesteps}"
                )
            self.logger.record("oath/win_rate", wr)
            self.logger.record("oath/total_games", total)
            self._last_log_time = now

        return True


def make_env(rank, opponent, seed):
    """Create a single environment instance for vectorization."""
    def _init():
        env = OathSingleAgentWrapper(
            player_id=1,
            opponent=opponent,
            seed=seed + rank if seed is not None else None,
        )
        env = ActionMasker(env, mask_fn)
        return env
    return _init


def main():
    parser = argparse.ArgumentParser(description="Train Oath RL agent")
    parser.add_argument("--timesteps", type=int, default=1_000_000,
                        help="Total training timesteps (default: 1M)")
    parser.add_argument("--opponent", choices=["random", "heuristic"],
                        default="heuristic",
                        help="Fill agent type for other exiles")
    parser.add_argument("--n-envs", type=int, default=4,
                        help="Number of parallel environments")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint to resume from")
    parser.add_argument("--output-dir", type=str, default="models",
                        help="Directory to save models")
    parser.add_argument("--lr", type=float, default=3e-4,
                        help="Learning rate")
    parser.add_argument("--n-steps", type=int, default=2048,
                        help="Steps per rollout per env")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Minibatch size")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.seed is not None:
        set_random_seed(args.seed)

    print(f"Training config:")
    print(f"  Timesteps:  {args.timesteps:,}")
    print(f"  Opponent:   {args.opponent}")
    print(f"  Envs:       {args.n_envs}")
    print(f"  LR:         {args.lr}")
    print(f"  N-steps:    {args.n_steps}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Seed:       {args.seed}")
    print(f"  Resume:     {args.resume or 'no'}")
    print()

    # Create vectorized envs
    env_fns = [make_env(i, args.opponent, args.seed) for i in range(args.n_envs)]
    if args.n_envs == 1:
        vec_env = DummyVecEnv(env_fns)
    else:
        vec_env = SubprocVecEnv(env_fns)

    # Create or load model
    if args.resume:
        print(f"Resuming from {args.resume}")
        model = MaskablePPO.load(args.resume, env=vec_env)
        model.learning_rate = args.lr
    else:
        model = MaskablePPO(
            "MultiInputPolicy",
            vec_env,
            learning_rate=args.lr,
            n_steps=args.n_steps,
            batch_size=args.batch_size,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            verbose=1,
            seed=args.seed,
        )

    # Callbacks
    checkpoint_cb = CheckpointCallback(
        save_freq=max(50_000 // args.n_envs, 1),
        save_path=args.output_dir,
        name_prefix="oath_exile",
    )
    winrate_cb = WinRateCallback(window=100)
    callbacks = CallbackList([checkpoint_cb, winrate_cb])

    # Train
    print("Starting training...")
    t0 = time.time()
    model.learn(total_timesteps=args.timesteps, callback=callbacks)
    elapsed = time.time() - t0

    # Save final model
    final_path = os.path.join(args.output_dir, "oath_exile_latest")
    model.save(final_path)
    print(f"\nTraining complete in {elapsed/60:.1f} minutes")
    print(f"Model saved to {final_path}.zip")

    # Print final stats
    if winrate_cb.results:
        last_100 = winrate_cb.results[-100:]
        wr = sum(last_100) / len(last_100) * 100
        print(f"Final win rate (last {len(last_100)} games): {wr:.1f}%")
        print(f"Total games played: {len(winrate_cb.results)}")

    vec_env.close()


if __name__ == "__main__":
    main()

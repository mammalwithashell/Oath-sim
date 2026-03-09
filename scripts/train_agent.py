"""Train an RL agent for Oath using MaskablePPO (sb3-contrib).

Uses a single-agent wrapper where the RL agent plays as one exile,
other exiles use a fill agent, and the Chancellor is optionally played
by the Clockwork Prince automa.

Features:
    - 4-stage curriculum: random -> heuristic -> clockwork-prince -> self-play
    - Self-play with snapshot pool
    - Diagnostic QA checkpoints between curriculum stages
    - 20K-step smoke test mode
    - TensorBoard + optional W&B logging

Usage:
    # Basic training against heuristic opponents
    python scripts/train_agent.py

    # 20K step smoke test (validates pipeline end-to-end)
    python scripts/train_agent.py --smoke-test

    # Full curriculum with self-play
    python scripts/train_agent.py --curriculum --self-play --timesteps 2000000

    # Resume from checkpoint
    python scripts/train_agent.py --resume models/oath_exile_latest.zip
"""

import argparse
import os
import random as stdlib_random
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
from oath.enums import OathGoal
from oath.engine.actions import IllegalActionError
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent


# ---------------------------------------------------------------------------
# Self-play agent wrapper
# ---------------------------------------------------------------------------

class SBAgentWrapper:
    """Wraps a frozen MaskablePPO model behind the act() interface."""

    def __init__(self, model_path: str, seed=None):
        self.model = MaskablePPO.load(model_path)
        self.rng = np.random.default_rng(seed)

    def act(self, observation: dict) -> int:
        mask = np.array(observation["action_mask"], dtype=bool)
        # Only pass keys the model expects (observation + action_mask)
        filtered_obs = {
            "observation": observation["observation"],
            "action_mask": observation["action_mask"],
        }
        try:
            action, _ = self.model.predict(
                filtered_obs,
                action_masks=mask,
                deterministic=False,
            )
            return int(action)
        except Exception as e:
            print(f"[SBAgentWrapper] predict failed: {e}", flush=True)
            # Fallback: pick a random valid action
            valid = np.where(mask)[0]
            return int(self.rng.choice(valid))


class SnapshotPool:
    """Maintains a pool of recent model snapshots for self-play diversity."""

    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self.snapshots: list[str] = []
        self.rng = np.random.default_rng()

    def add(self, path: str):
        self.snapshots.append(path)
        if len(self.snapshots) > self.max_size:
            # Remove oldest snapshot file
            old = self.snapshots.pop(0)
            if os.path.exists(old):
                os.remove(old)

    def sample(self) -> str | None:
        if not self.snapshots:
            return None
        return self.rng.choice(self.snapshots)

    def latest(self) -> str | None:
        return self.snapshots[-1] if self.snapshots else None


# ---------------------------------------------------------------------------
# Single-agent wrapper
# ---------------------------------------------------------------------------

class OathSingleAgentWrapper(Env):
    """Wraps Oath's multi-agent env for single-agent RL training.

    The RL agent controls one exile player. Other exiles use a fill agent
    (random or heuristic). Chancellor is played by the Clockwork Prince
    (when enabled) or by the fill agent.
    """

    def __init__(self, player_id=1, opponent="heuristic", seed=None,
                 clockwork_prince=True):
        super().__init__()
        self.player_id = player_id
        self.player_name = f"player_{player_id}"
        self._seed = seed
        self._opponent_type = opponent
        self._clockwork_prince = clockwork_prince

        self._env = OathEnv(num_players=4, clockwork_prince=clockwork_prince,
                            seed=seed)
        self._fill_agent = self._make_fill_agent(opponent, seed)

        obs_space = self._env.observation_space(self.player_name)
        self.observation_space = spaces.Dict({
            "observation": obs_space["observation"],
            "action_mask": obs_space["action_mask"],
        })
        self.action_space = self._env.action_space(self.player_name)

        self._rng = np.random.default_rng(seed)
        self._episode_reward = 0.0
        self._episode_length = 0
        self._wins = 0
        self._games = 0
        self._last_vowed_oath = None
        self._last_won = False
        self._win_streak = 0
        self._empire_threshold = 3  # Knockdown after N consecutive wins

    @staticmethod
    def _make_fill_agent(opponent, seed):
        if opponent == "random":
            return RandomAgent(seed=seed)
        if opponent == "heuristic":
            return HeuristicAgent(seed=seed)
        # For self-play, caller sets agent via set_opponent()
        return HeuristicAgent(seed=seed)

    def set_opponent(self, agent):
        """Hot-swap the fill agent (used by curriculum/self-play callbacks)."""
        self._fill_agent = agent

    def set_clockwork_prince(self, enabled: bool):
        """Toggle Clockwork Prince mode (takes effect on next reset)."""
        self._clockwork_prince = enabled

    def reset(self, seed=None, options=None):
        # Empire knockdown: after N consecutive wins, break the streak
        if self._win_streak >= self._empire_threshold:
            oath_goal = OathGoal(self._rng.choice(list(OathGoal)))
            print(f"[Empire knockdown] {self._win_streak} wins in a row "
                  f"(threshold={self._empire_threshold}), resetting to random "
                  f"oath={oath_goal.name}. Next threshold={self._empire_threshold + 2}",
                  flush=True)
            self._empire_threshold += 2
            self._win_streak = 0
            self._last_vowed_oath = None
            self._last_won = False
        elif self._last_won and self._last_vowed_oath is not None:
            oath_goal = self._last_vowed_oath
        else:
            oath_goal = OathGoal(self._rng.choice(list(OathGoal)))
        self._last_vowed_oath = None
        self._last_won = False
        self._env = OathEnv(
            num_players=4, clockwork_prince=self._clockwork_prince,
            seed=seed, oath_goal=oath_goal,
        )
        self._env.reset(seed=seed)
        self._advance_to_player()
        obs = self._get_obs()
        self._episode_reward = 0.0
        self._episode_length = 0
        return obs, {}

    def step(self, action):
        try:
            self._env.step(int(action))
        except IllegalActionError:
            # Mask/state mismatch edge case — fall back to END_ACT_PHASE
            try:
                self._env.step(43)
            except (IllegalActionError, Exception):
                # If even that fails, step with None to skip
                self._env.step(None)
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
            gs = self._env.game_state
            won = (gs is not None and gs.winner == self.player_id)
            if won:
                self._wins += 1
                self._win_streak += 1
            else:
                self._win_streak = 0
            # Capture vowed oath for next episode
            if gs is not None and gs.vowed_oath is not None:
                self._last_vowed_oath = gs.vowed_oath
                self._last_won = won
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
                try:
                    self._env.step(action)
                except IllegalActionError:
                    self._env.step(43)  # END_ACT_PHASE fallback

    def action_masks(self):
        """Return current action mask for MaskablePPO."""
        obs = self._get_obs()
        return np.array(obs["action_mask"], dtype=bool)


def mask_fn(env):
    """Extract action mask from the wrapped environment."""
    return env.action_masks()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

CURRICULUM_STAGES = [
    {"name": "random",           "opponent": "random",    "clockwork_prince": False},
    {"name": "heuristic",        "opponent": "heuristic", "clockwork_prince": False},
    {"name": "clockwork-prince", "opponent": "heuristic", "clockwork_prince": True},
    {"name": "self-play",        "opponent": "self-play", "clockwork_prince": True},
]


class WinRateCallback(BaseCallback):
    """Logs win rate and episode reward over a rolling window."""

    def __init__(self, window=100, verbose=1):
        super().__init__(verbose)
        self.window = window
        self.results: list[bool] = []
        self.rewards: list[float] = []
        self._last_log_time = 0

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            ep = info.get("episode")
            if ep:
                self.results.append(ep["won"])
                self.rewards.append(ep["r"])

        now = time.time()
        if now - self._last_log_time > 30 and len(self.results) >= 10:
            recent_wins = self.results[-self.window:]
            recent_rewards = self.rewards[-self.window:]
            wr = sum(recent_wins) / len(recent_wins) * 100
            avg_r = sum(recent_rewards) / len(recent_rewards)
            total = len(self.results)

            if self.verbose:
                print(
                    f"  [WinRate] {total} games | "
                    f"last {len(recent_wins)}: {wr:.1f}% wins | "
                    f"avg reward: {avg_r:.3f} | "
                    f"timesteps: {self.num_timesteps}"
                )
            self.logger.record("oath/win_rate", wr)
            self.logger.record("oath/episode_reward_mean", avg_r)
            self.logger.record("oath/total_games", total)
            self._last_log_time = now

        return True

    def get_win_rate(self, window: int | None = None) -> float:
        """Return rolling win rate as a fraction [0, 1]."""
        w = window or self.window
        if len(self.results) < 10:
            return 0.0
        recent = self.results[-w:]
        return sum(recent) / len(recent)


class CurriculumCallback(BaseCallback):
    """Automatically promotes opponent difficulty based on win rate."""

    def __init__(
        self,
        winrate_cb: WinRateCallback,
        promote_threshold: float = 0.35,
        promote_window: int = 200,
        enable_self_play: bool = False,
        snapshot_pool: SnapshotPool | None = None,
        output_dir: str = "models",
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.winrate_cb = winrate_cb
        self.promote_threshold = promote_threshold
        self.promote_window = promote_window
        self.enable_self_play = enable_self_play
        self.snapshot_pool = snapshot_pool
        self.output_dir = output_dir

        # Determine available stages
        self.stages = [s for s in CURRICULUM_STAGES]
        if not self.enable_self_play:
            self.stages = [s for s in self.stages if s["opponent"] != "self-play"]

        self.current_stage = 0
        self._last_check_games = 0

    def _on_training_start(self):
        self._set_opponents(self.stages[self.current_stage])

    def _on_step(self) -> bool:
        total_games = len(self.winrate_cb.results)
        self.logger.record("oath/curriculum_stage", self.current_stage)
        self.logger.record("oath/opponent_type", self.stages[self.current_stage]["name"])

        # Only check promotion every 50 games
        if total_games - self._last_check_games < 50:
            return True
        self._last_check_games = total_games

        if self.current_stage >= len(self.stages) - 1:
            return True  # Already at final stage

        wr = self.winrate_cb.get_win_rate(self.promote_window)
        if wr >= self.promote_threshold:
            self.current_stage += 1
            stage = self.stages[self.current_stage]
            if self.verbose:
                print(
                    f"\n{'='*60}\n"
                    f"  CURRICULUM: Promoted to stage {self.current_stage} "
                    f"({stage['name']}) at {wr*100:.1f}% win rate\n"
                    f"{'='*60}\n"
                )
            # Run diagnostic checkpoint on the outgoing stage
            prev_stage = self.stages[self.current_stage - 1]
            prev_cp = prev_stage.get("clockwork_prince", True)
            run_diagnostic_checkpoint(
                self.model, prev_stage["name"], self.output_dir,
                clockwork_prince=prev_cp, num_games=20,
            )
            # Reset win tracking for new stage
            self.winrate_cb.results.clear()
            self.winrate_cb.rewards.clear()
            self._last_check_games = 0
            self._set_opponents(stage)

        return True

    def _set_opponents(self, stage: dict):
        """Swap fill agents and clockwork prince setting in all sub-environments."""
        opponent_type = stage["opponent"]
        use_cp = stage.get("clockwork_prince", True)
        vec_env = self.model.get_env()

        if opponent_type == "self-play":
            self._set_self_play_opponents(vec_env, use_cp)
        else:
            for i in range(vec_env.num_envs):
                env = self._get_inner_env(vec_env, i)
                if env is None:
                    continue
                env.set_clockwork_prince(use_cp)
                if opponent_type == "random":
                    env.set_opponent(RandomAgent(seed=i))
                else:
                    env.set_opponent(HeuristicAgent(seed=i))

    def _set_self_play_opponents(self, vec_env, clockwork_prince=True):
        """Set opponents to frozen snapshots of the current model."""
        if self.snapshot_pool is None:
            return
        # Save current model as a snapshot
        snap_path = os.path.join(
            self.output_dir,
            f"snapshot_{self.num_timesteps}.zip"
        )
        self.model.save(snap_path)
        self.snapshot_pool.add(snap_path)

        for i in range(vec_env.num_envs):
            env = self._get_inner_env(vec_env, i)
            if env is None:
                continue
            env.set_clockwork_prince(clockwork_prince)
            chosen = self.snapshot_pool.sample()
            if chosen:
                env.set_opponent(SBAgentWrapper(chosen, seed=i))

    @staticmethod
    def _get_inner_env(vec_env, idx: int):
        """Extract the OathSingleAgentWrapper from a vectorized env."""
        # DummyVecEnv stores envs in .envs, SubprocVecEnv uses .env_method
        if hasattr(vec_env, "envs"):
            # DummyVecEnv — unwrap ActionMasker -> OathSingleAgentWrapper
            env = vec_env.envs[idx]
            return env.env if hasattr(env, "env") else env
        else:
            # SubprocVecEnv — can't directly access, use env_method
            return None  # handled in _set_opponents_subproc


class SelfPlayCallback(BaseCallback):
    """Periodically saves model snapshots and updates self-play opponents."""

    def __init__(
        self,
        snapshot_pool: SnapshotPool,
        snapshot_freq: int = 50_000,
        output_dir: str = "models",
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.snapshot_pool = snapshot_pool
        self.snapshot_freq = snapshot_freq
        self.output_dir = output_dir
        self._last_snapshot_step = 0

    def _on_step(self) -> bool:
        if self.num_timesteps - self._last_snapshot_step < self.snapshot_freq:
            return True

        self._last_snapshot_step = self.num_timesteps

        # Save snapshot
        snap_path = os.path.join(
            self.output_dir,
            f"snapshot_{self.num_timesteps}.zip"
        )
        self.model.save(snap_path)
        self.snapshot_pool.add(snap_path)

        if self.verbose:
            print(
                f"  [SelfPlay] Saved snapshot at step {self.num_timesteps} "
                f"(pool size: {len(self.snapshot_pool.snapshots)})"
            )

        # Update opponents in DummyVecEnv
        vec_env = self.model.get_env()
        if hasattr(vec_env, "envs"):
            chosen = self.snapshot_pool.sample()
            if chosen:
                shared_agent = SBAgentWrapper(chosen, seed=0)
                for i in range(vec_env.num_envs):
                    env = vec_env.envs[i]
                    inner = env.env if hasattr(env, "env") else env
                    inner.set_opponent(shared_agent)

        return True


# ---------------------------------------------------------------------------
# Environment factory
# ---------------------------------------------------------------------------

def make_env(rank, opponent, seed, clockwork_prince=True):
    """Create a single environment instance for vectorization."""
    def _init():
        env = OathSingleAgentWrapper(
            player_id=1,
            opponent=opponent,
            seed=seed + rank if seed is not None else None,
            clockwork_prince=clockwork_prince,
        )
        env = ActionMasker(env, mask_fn)
        return env
    return _init


# ---------------------------------------------------------------------------
# Diagnostic checkpoint (runs between curriculum stages)
# ---------------------------------------------------------------------------

def run_diagnostic_checkpoint(model, stage_name, output_dir, clockwork_prince=True,
                              num_games=20, seed=42):
    """Run a QA checkpoint: save model, evaluate, check for degenerate behavior."""
    checkpoint_path = os.path.join(output_dir, f"stage_{stage_name}")
    model.save(checkpoint_path)

    # Quick evaluation inline (avoid subprocess)
    from collections import Counter
    agent_model = model
    fill_agent = HeuristicAgent(seed=seed)
    player_id = 1
    wins = 0
    action_counts = Counter()
    win_types = Counter()

    for game_idx in range(num_games):
        game_seed = seed + game_idx
        env = OathEnv(num_players=4, clockwork_prince=clockwork_prince,
                      seed=game_seed)
        env.reset()
        player_name = f"player_{player_id}"

        steps = 0
        for _ in env.agent_iter():
            if steps > 5000:
                break  # Safety limit
            steps += 1
            obs, reward, term, trunc, info = env.last()
            if term or trunc:
                env.step(None)
                continue
            if env.agent_selection == player_name:
                mask = np.array(obs["action_mask"], dtype=bool)
                filtered = {"observation": obs["observation"],
                            "action_mask": obs["action_mask"]}
                try:
                    action, _ = agent_model.predict(filtered, action_masks=mask,
                                                    deterministic=True)
                    action = int(action)
                except Exception:
                    valid = np.where(mask)[0]
                    action = int(np.random.choice(valid))
                action_counts[action] += 1
            else:
                action = fill_agent.act(obs)
            try:
                env.step(action)
            except Exception:
                break

        gs = env.game_state
        if gs is not None and gs.winner == player_id:
            wins += 1
        wt = gs.win_type.name if gs is not None and gs.win_type is not None else "UNKNOWN"
        win_types[wt] += 1

    win_rate = wins / num_games
    total_actions = sum(action_counts.values())

    # Check for degenerate behavior
    warnings = []
    if total_actions > 0:
        top_action_id, top_count = action_counts.most_common(1)[0]
        top_pct = top_count / total_actions * 100
        if top_pct > 80:
            warnings.append(f"Single action #{top_action_id} is {top_pct:.0f}% of all actions")
    if len(action_counts) < 5:
        warnings.append(f"Only {len(action_counts)} distinct actions used")
    if win_rate == 0.0 and num_games >= 10:
        warnings.append("0% win rate — agent may not be learning")

    # Print QA report
    print(f"\n  [QA] Stage '{stage_name}' checkpoint ({num_games} games):")
    print(f"    Win rate: {win_rate*100:.1f}%")
    print(f"    Win types: {dict(win_types)}")
    print(f"    Distinct actions: {len(action_counts)}")
    if action_counts:
        top3 = action_counts.most_common(3)
        print(f"    Top actions: {', '.join(f'#{a}({c}x)' for a, c in top3)}")
    if warnings:
        for w in warnings:
            print(f"    WARNING: {w}")
    else:
        print(f"    No degenerate behavior detected")
    print(f"    Checkpoint saved: {checkpoint_path}.zip\n")

    return {"win_rate": win_rate, "warnings": warnings}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train Oath RL agent")

    # Core training args
    parser.add_argument("--timesteps", type=int, default=1_000_000,
                        help="Total training timesteps (default: 1M)")
    parser.add_argument("--opponent", choices=["random", "heuristic"],
                        default="heuristic",
                        help="Fill agent type (without curriculum)")
    parser.add_argument("--n-envs", type=int, default=4,
                        help="Number of parallel environments")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint to resume from")
    parser.add_argument("--output-dir", type=str, default="models",
                        help="Directory to save models")

    # Hyperparameters
    parser.add_argument("--lr", type=float, default=3e-4,
                        help="Learning rate")
    parser.add_argument("--n-steps", type=int, default=2048,
                        help="Steps per rollout per env")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Minibatch size")

    # Curriculum learning
    parser.add_argument("--curriculum", action="store_true",
                        help="Enable curriculum (random -> heuristic -> clockwork-prince -> self-play)")
    parser.add_argument("--promote-threshold", type=float, default=0.35,
                        help="Win rate threshold to promote curriculum stage")
    parser.add_argument("--promote-window", type=int, default=200,
                        help="Rolling window size for promotion check")

    # Self-play
    parser.add_argument("--self-play", action="store_true",
                        help="Enable self-play as final curriculum stage")
    parser.add_argument("--snapshot-freq", type=int, default=50_000,
                        help="Timesteps between self-play snapshots")
    parser.add_argument("--snapshot-pool", type=int, default=5,
                        help="Number of recent snapshots to keep")

    # Logging
    parser.add_argument("--wandb", action="store_true",
                        help="Enable Weights & Biases logging")
    parser.add_argument("--run-name", type=str, default=None,
                        help="Experiment run name")
    parser.add_argument("--tensorboard-dir", type=str, default="logs",
                        help="TensorBoard log directory")

    # Smoke test
    parser.add_argument("--smoke-test", action="store_true",
                        help="Run 20K step smoke test through all 4 stages")

    args = parser.parse_args()

    # Smoke test overrides
    if args.smoke_test:
        print("[SMOKE TEST] Running 20K step end-to-end pipeline validation\n")
        args.timesteps = 20_000
        args.curriculum = True
        args.self_play = True
        args.promote_threshold = 0.15
        args.promote_window = 20
        args.n_envs = 1

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.tensorboard_dir, exist_ok=True)

    if args.seed is not None:
        set_random_seed(args.seed)

    # Determine starting opponent and clockwork prince setting
    start_opponent = "random" if args.curriculum else args.opponent
    start_cp = False if args.curriculum else True

    # Run name
    run_name = args.run_name or f"oath_{start_opponent}_{int(time.time())}"

    print(f"Training config:")
    print(f"  Timesteps:    {args.timesteps:,}")
    print(f"  Opponent:     {start_opponent}" +
          (" (curriculum)" if args.curriculum else ""))
    print(f"  Envs:         {args.n_envs}")
    print(f"  LR:           {args.lr}")
    print(f"  N-steps:      {args.n_steps}")
    print(f"  Batch size:   {args.batch_size}")
    print(f"  Seed:         {args.seed}")
    print(f"  Resume:       {args.resume or 'no'}")
    print(f"  Curriculum:   {args.curriculum}")
    print(f"  Self-play:    {args.self_play}")
    print(f"  Clockwork P:  {start_cp}" +
          (" (enables at stage 2)" if args.curriculum else ""))
    print(f"  TensorBoard:  {args.tensorboard_dir}")
    print(f"  W&B:          {args.wandb}")
    print(f"  Run name:     {run_name}")
    print()

    # W&B init
    if args.wandb:
        try:
            import wandb
            wandb.init(
                project="oath-rl",
                name=run_name,
                config=vars(args),
                sync_tensorboard=True,
            )
        except ImportError:
            print("WARNING: wandb not installed. Install with: pip install wandb")
            print("Continuing without W&B logging.\n")
            args.wandb = False

    # Create vectorized envs (use DummyVecEnv for curriculum/self-play
    # since we need direct access to swap opponents)
    env_fns = [make_env(i, start_opponent, args.seed, clockwork_prince=start_cp)
               for i in range(args.n_envs)]
    use_dummy = args.n_envs == 1 or args.curriculum or args.self_play
    if use_dummy:
        vec_env = DummyVecEnv(env_fns)
    else:
        vec_env = SubprocVecEnv(env_fns)

    # TensorBoard log path
    tb_log = os.path.join(args.tensorboard_dir, "oath_training")

    # Create or load model
    if args.resume:
        print(f"Resuming from {args.resume}")
        model = MaskablePPO.load(
            args.resume,
            env=vec_env,
            tensorboard_log=tb_log,
        )
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
            tensorboard_log=tb_log,
        )

    # Build callback list
    callbacks = []

    # Checkpoint saving
    checkpoint_cb = CheckpointCallback(
        save_freq=max(50_000 // args.n_envs, 1),
        save_path=args.output_dir,
        name_prefix="oath_exile",
    )
    callbacks.append(checkpoint_cb)

    # Win rate tracking
    winrate_cb = WinRateCallback(window=100)
    callbacks.append(winrate_cb)

    # Snapshot pool (shared between curriculum and self-play callbacks)
    snapshot_pool = SnapshotPool(max_size=args.snapshot_pool) if args.self_play else None

    # Curriculum learning
    if args.curriculum:
        curriculum_cb = CurriculumCallback(
            winrate_cb=winrate_cb,
            promote_threshold=args.promote_threshold,
            promote_window=args.promote_window,
            enable_self_play=args.self_play,
            snapshot_pool=snapshot_pool,
            output_dir=args.output_dir,
            verbose=1,
        )
        callbacks.append(curriculum_cb)

    # Self-play snapshot updates (runs even without curriculum, if self-play enabled)
    if args.self_play and snapshot_pool:
        selfplay_cb = SelfPlayCallback(
            snapshot_pool=snapshot_pool,
            snapshot_freq=args.snapshot_freq,
            output_dir=args.output_dir,
            verbose=1,
        )
        callbacks.append(selfplay_cb)

    callback_list = CallbackList(callbacks)

    # Train
    print("Starting training...")
    t0 = time.time()
    model.learn(
        total_timesteps=args.timesteps,
        callback=callback_list,
        tb_log_name=run_name,
    )
    elapsed = time.time() - t0

    # Save final model
    final_path = os.path.join(args.output_dir, "oath_exile_latest")
    model.save(final_path)
    print(f"\nTraining complete in {elapsed/60:.1f} minutes")
    print(f"Model saved to {final_path}.zip")

    # Run final diagnostic checkpoint
    if args.curriculum or args.smoke_test:
        diag_games = 10 if args.smoke_test else 20
        run_diagnostic_checkpoint(model, "final", args.output_dir,
                                  clockwork_prince=True, num_games=diag_games)

    # Print final stats
    if winrate_cb.results:
        last_100 = winrate_cb.results[-100:]
        wr = sum(last_100) / len(last_100) * 100
        print(f"Final win rate (last {len(last_100)} games): {wr:.1f}%")
        print(f"Total games played: {len(winrate_cb.results)}")

    vec_env.close()

    if args.wandb:
        try:
            import wandb
            wandb.finish()
        except ImportError:
            pass


if __name__ == "__main__":
    main()

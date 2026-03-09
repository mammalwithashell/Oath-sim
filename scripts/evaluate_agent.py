"""Evaluate a trained RL agent against different opponent types.

Usage:
    # Evaluate against all opponent types
    python scripts/evaluate_agent.py models/oath_exile_latest.zip

    # Specific opponent, more games
    python scripts/evaluate_agent.py models/oath_exile_latest.zip --opponent heuristic --num-games 100

    # Deterministic play
    python scripts/evaluate_agent.py models/oath_exile_latest.zip --deterministic --seed 42
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oath.env.oath_env import OathEnv
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent


class TrainedAgent:
    """Wraps a MaskablePPO model for evaluation."""

    def __init__(self, model_path: str, deterministic: bool = False):
        self.model = MaskablePPO.load(model_path)
        self.deterministic = deterministic

    def act(self, observation: dict) -> int:
        mask = np.array(observation["action_mask"], dtype=bool)
        action, _ = self.model.predict(
            observation,
            action_masks=mask,
            deterministic=self.deterministic,
        )
        return int(action)


def evaluate(
    model_path: str,
    opponent: str,
    num_games: int,
    deterministic: bool = False,
    seed: int | None = None,
    clockwork_prince: bool = True,
) -> dict:
    """Run evaluation games and return stats."""
    agent = TrainedAgent(model_path, deterministic=deterministic)
    fill_agent = RandomAgent(seed=seed) if opponent == "random" else HeuristicAgent(seed=seed)

    player_id = 1
    wins = 0
    total_rewards = []

    for game_idx in range(num_games):
        game_seed = (seed + game_idx) if seed is not None else None
        env = OathEnv(num_players=4, clockwork_prince=clockwork_prince,
                      seed=game_seed)
        env.reset()

        cumulative_reward = 0.0

        for _ in env.agent_iter():
            obs, reward, term, trunc, info = env.last()

            if env.agent_selection == f"player_{player_id}":
                cumulative_reward += reward

            if term or trunc:
                env.step(None)
                continue

            if env.agent_selection == f"player_{player_id}":
                action = agent.act(obs)
            else:
                action = fill_agent.act(obs)
            env.step(action)

        if env.game_state is not None and env.game_state.winner == player_id:
            wins += 1
        total_rewards.append(cumulative_reward)

    win_rate = wins / num_games
    # Wilson score 95% CI
    z = 1.96
    n = num_games
    p = win_rate
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    ci_low = max(0, center - margin)
    ci_high = min(1, center + margin)

    return {
        "opponent": opponent,
        "games": num_games,
        "wins": wins,
        "win_rate": win_rate,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "avg_reward": np.mean(total_rewards),
        "std_reward": np.std(total_rewards),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained Oath agent")
    parser.add_argument("model", type=str, help="Path to trained model (.zip)")
    parser.add_argument("--opponent", type=str, default=None,
                        choices=["random", "heuristic", "all"],
                        help="Opponent type (default: all)")
    parser.add_argument("--num-games", type=int, default=50,
                        help="Number of evaluation games per opponent")
    parser.add_argument("--deterministic", action="store_true",
                        help="Use deterministic action selection")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    parser.add_argument("--no-clockwork-prince", action="store_true",
                        help="Disable Clockwork Prince (Chancellor uses fill agent)")
    args = parser.parse_args()

    opponents = ["random", "heuristic"] if args.opponent in (None, "all") else [args.opponent]

    print(f"Evaluating: {args.model}")
    print(f"Games per opponent: {args.num_games}")
    print(f"Deterministic: {args.deterministic}")
    print()

    for opp in opponents:
        print(f"vs {opp}...", end=" ", flush=True)
        result = evaluate(
            args.model,
            opponent=opp,
            num_games=args.num_games,
            deterministic=args.deterministic,
            seed=args.seed,
            clockwork_prince=not args.no_clockwork_prince,
        )
        print(
            f"{result['wins']}/{result['games']} wins "
            f"({result['win_rate']*100:.1f}% "
            f"[{result['ci_low']*100:.1f}-{result['ci_high']*100:.1f}%]) | "
            f"avg reward: {result['avg_reward']:.3f} "
            f"(std: {result['std_reward']:.3f})"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()

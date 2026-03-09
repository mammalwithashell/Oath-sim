"""Diagnose a trained RL agent by replaying games with full action logging.

Shows exactly what actions the agent takes, how games end, and whether
the agent has found an exploit or degenerate strategy.

Usage:
    python scripts/diagnose_agent.py models/phase3-selfplay/oath_exile_50000_steps.zip
    python scripts/diagnose_agent.py models/oath_exile_latest.zip --num-games 20 --verbose
    python scripts/diagnose_agent.py models/oath_exile_latest.zip --opponent random --seed 42
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oath.env.oath_env import OathEnv
from oath.enums import WinType
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent
from oath.display.renderer import describe_action


class TrainedAgent:
    """Wraps a MaskablePPO model for diagnosis."""

    def __init__(self, model_path: str, deterministic: bool = True):
        self.model = MaskablePPO.load(model_path)
        self.deterministic = deterministic

    def act(self, observation: dict) -> int:
        mask = np.array(observation["action_mask"], dtype=bool)
        # Only pass keys the model expects (observation + action_mask)
        filtered_obs = {
            "observation": observation["observation"],
            "action_mask": observation["action_mask"],
        }
        action, _ = self.model.predict(
            filtered_obs,
            action_masks=mask,
            deterministic=self.deterministic,
        )
        return int(action)


def run_game(env, agent, fill_agent, player_id):
    """Play one game and return (actions_log, game_summary)."""
    env.reset()
    player_name = f"player_{player_id}"
    actions_log = []

    for _ in env.agent_iter():
        obs, reward, term, trunc, info = env.last()
        current_player = env.agent_selection

        if term or trunc:
            env.step(None)
            continue

        current_idx = int(current_player.split("_")[1])
        gs = env.game_state

        # Choose action
        if current_player == player_name:
            action = agent.act(obs)
        else:
            action = fill_agent.act(obs)

        # Log the action
        try:
            desc = describe_action(action, gs, current_idx)
        except Exception:
            desc = f"action_{action}"

        actions_log.append({
            "round": gs.round_number,
            "player": current_player,
            "player_idx": current_idx,
            "action_id": action,
            "description": desc,
            "phase": gs.current_phase.name if hasattr(gs, "current_phase") else "?",
            "is_rl_agent": current_player == player_name,
        })

        env.step(action)

    # Build game summary
    gs = env.game_state
    won = gs is not None and gs.winner == player_id
    win_type = gs.win_type.name if gs is not None and gs.win_type is not None else "UNKNOWN"
    winner = gs.winner if gs is not None else None

    summary = {
        "won": won,
        "winner": winner,
        "win_type": win_type,
        "rounds": gs.round_number if gs is not None else 0,
        "total_actions": len(actions_log),
        "rl_actions": sum(1 for a in actions_log if a["is_rl_agent"]),
    }
    return actions_log, summary


def print_game_trace(game_idx, actions_log, summary):
    """Print detailed action-by-action trace for one game."""
    print(f"\n{'='*70}")
    print(f"  GAME {game_idx + 1}: {summary['total_actions']} actions, "
          f"{summary['rounds']} rounds, winner=P{summary['winner']} "
          f"({summary['win_type']}), RL {'WON' if summary['won'] else 'LOST'}")
    print(f"{'='*70}")

    current_round = None
    for entry in actions_log:
        if entry["round"] != current_round:
            current_round = entry["round"]
            print(f"\n  --- Round {current_round} ---")

        marker = " >>> " if entry["is_rl_agent"] else "     "
        print(f"{marker}{entry['player']} [{entry['phase']:>8}] "
              f"#{entry['action_id']:>3}: {entry['description']}")


def print_aggregate_stats(all_summaries, all_logs, player_id):
    """Print aggregate statistics across all games."""
    print(f"\n{'='*70}")
    print("  AGGREGATE STATISTICS")
    print(f"{'='*70}\n")

    # Win rate
    wins = sum(1 for s in all_summaries if s["won"])
    total = len(all_summaries)
    print(f"Win rate: {wins}/{total} ({wins/total*100:.1f}%)")

    # Game length
    lengths = [s["total_actions"] for s in all_summaries]
    rl_lengths = [s["rl_actions"] for s in all_summaries]
    rounds = [s["rounds"] for s in all_summaries]
    print(f"Avg total actions: {np.mean(lengths):.1f} (min={min(lengths)}, max={max(lengths)})")
    print(f"Avg RL actions:    {np.mean(rl_lengths):.1f} (min={min(rl_lengths)}, max={max(rl_lengths)})")
    print(f"Avg rounds:        {np.mean(rounds):.1f} (min={min(rounds)}, max={max(rounds)})")

    # Win type distribution
    print(f"\nWin type distribution:")
    win_types = Counter(s["win_type"] for s in all_summaries)
    for wt, count in win_types.most_common():
        print(f"  {wt:25s}: {count:3d} ({count/total*100:.1f}%)")

    # Winner distribution
    print(f"\nWinner distribution:")
    winners = Counter(s["winner"] for s in all_summaries)
    for w, count in winners.most_common():
        label = f"P{w} (RL)" if w == player_id else f"P{w}"
        print(f"  {label:25s}: {count:3d} ({count/total*100:.1f}%)")

    # RL agent action frequency
    rl_actions = []
    for log in all_logs:
        for entry in log:
            if entry["is_rl_agent"]:
                rl_actions.append(entry["action_id"])

    print(f"\nRL agent action frequency (top 15):")
    action_counts = Counter(rl_actions)
    for action_id, count in action_counts.most_common(15):
        # Get a representative description
        desc = f"action_{action_id}"
        for log in all_logs:
            for entry in log:
                if entry["action_id"] == action_id and entry["is_rl_agent"]:
                    desc = entry["description"]
                    break
            if desc != f"action_{action_id}":
                break
        print(f"  #{action_id:>3} ({count:4d}x): {desc}")

    # Opening sequence analysis (first N RL actions per game)
    print(f"\nRL opening sequences (first 5 actions):")
    openers = Counter()
    for log in all_logs:
        rl_seq = [str(e["action_id"]) for e in log if e["is_rl_agent"]][:5]
        if rl_seq:
            openers[" -> ".join(rl_seq)] += 1
    for seq, count in openers.most_common(5):
        print(f"  [{count:3d}x] {seq}")


def main():
    parser = argparse.ArgumentParser(description="Diagnose trained Oath agent behavior")
    parser.add_argument("model", type=str, help="Path to trained model (.zip)")
    parser.add_argument("--num-games", type=int, default=10,
                        help="Number of games to play (default: 10)")
    parser.add_argument("--opponent", type=str, default="heuristic",
                        choices=["random", "heuristic"],
                        help="Fill agent type (default: heuristic)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print detailed trace for ALL games (default: first 3)")
    parser.add_argument("--deterministic", action="store_true", default=True,
                        help="Use deterministic policy (default: True)")
    parser.add_argument("--no-deterministic", action="store_false", dest="deterministic",
                        help="Use stochastic policy")
    parser.add_argument("--no-clockwork-prince", action="store_true",
                        help="Disable Clockwork Prince (Chancellor uses fill agent)")
    args = parser.parse_args()

    player_id = 1

    print(f"Diagnosing: {args.model}")
    print(f"Games: {args.num_games}, Opponent: {args.opponent}, "
          f"Seed: {args.seed}, Deterministic: {args.deterministic}")
    print(f"RL agent is player_{player_id}")

    agent = TrainedAgent(args.model, deterministic=args.deterministic)
    fill_agent = (RandomAgent(seed=args.seed) if args.opponent == "random"
                  else HeuristicAgent(seed=args.seed))

    all_summaries = []
    all_logs = []

    for game_idx in range(args.num_games):
        game_seed = args.seed + game_idx
        use_cp = not args.no_clockwork_prince
        env = OathEnv(num_players=4, clockwork_prince=use_cp, seed=game_seed)

        actions_log, summary = run_game(env, agent, fill_agent, player_id)
        all_summaries.append(summary)
        all_logs.append(actions_log)

        # Print detailed trace for first 3 games (or all if --verbose)
        if args.verbose or game_idx < 3:
            print_game_trace(game_idx, actions_log, summary)
        else:
            # One-line summary
            print(f"  Game {game_idx + 1:3d}: {summary['total_actions']:3d} actions, "
                  f"{summary['rounds']} rounds, P{summary['winner']} wins "
                  f"({summary['win_type']})")

    print_aggregate_stats(all_summaries, all_logs, player_id)
    print("\nDone.")


if __name__ == "__main__":
    main()

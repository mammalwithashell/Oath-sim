#!/usr/bin/env python3
"""Run a chronicle evaluation with configurable agents.

Examples:
    # All random agents, 10 games
    python scripts/evaluate_chronicle.py

    # Heuristic exiles vs Clockwork Prince Chancellor
    python scripts/evaluate_chronicle.py --clockwork-prince \\
        --agent 1 heuristic --agent 2 heuristic --agent 3 heuristic

    # Multiple chronicles for statistical significance
    python scripts/evaluate_chronicle.py --num-chronicles 5 --seed 100

    # Short chronicle for quick testing
    python scripts/evaluate_chronicle.py --num-games 3
"""

import argparse
import sys

from oath.evaluation.evaluator import ChronicleEvaluator
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent


AGENT_TYPES = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,
}


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate agents over a chronicle sequence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--num-games", type=int, default=10,
                        help="Number of games per chronicle (default: 10)")
    parser.add_argument("--num-players", type=int, default=4,
                        help="Number of players (default: 4)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--max-iter", type=int, default=5000,
                        help="Max steps per game (default: 5000)")
    parser.add_argument("--clockwork-prince", action="store_true",
                        help="Use Clockwork Prince as Chancellor")
    parser.add_argument("--agent", action="append", nargs=2,
                        metavar=("PLAYER", "TYPE"),
                        help="Set agent for player index. TYPE: random, heuristic")
    parser.add_argument("--num-chronicles", type=int, default=1,
                        help="Run multiple chronicle sequences (default: 1)")
    args = parser.parse_args()

    # Build agent dict from --agent flags
    agents = {}
    if args.agent:
        for player_str, agent_type in args.agent:
            player_idx = int(player_str)
            agent_type = agent_type.lower()
            if agent_type not in AGENT_TYPES:
                print(f"Unknown agent type: {agent_type}. "
                      f"Available: {', '.join(AGENT_TYPES.keys())}",
                      file=sys.stderr)
                sys.exit(1)
            agents[player_idx] = AGENT_TYPES[agent_type](
                seed=args.seed + player_idx
            )

    # Run chronicle(s)
    for chronicle_idx in range(args.num_chronicles):
        if args.num_chronicles > 1:
            print(f"\n{'=' * 40}")
            print(f"Chronicle {chronicle_idx + 1}/{args.num_chronicles}")
            print(f"{'=' * 40}")

        evaluator = ChronicleEvaluator(
            num_players=args.num_players,
            num_games=args.num_games,
            agents=agents,
            clockwork_prince=args.clockwork_prince,
            seed=args.seed + chronicle_idx * 1000,
            max_iter_per_game=args.max_iter,
        )
        result = evaluator.run()
        print(ChronicleEvaluator.summarize(result))
        print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Play an interactive Oath game from the CLI.

Supports any mix of human and AI players (up to 6).

Examples:
    # Play as P1 (Exile) vs random agents
    python scripts/play_interactive.py --human 1

    # Two humans
    python scripts/play_interactive.py --human 1 --human 2

    # All 4 players human
    python scripts/play_interactive.py --human 0 --human 1 --human 2 --human 3

    # Play against Clockwork Prince + heuristic agents
    python scripts/play_interactive.py --human 1 --clockwork-prince \\
        --agent 2 heuristic --agent 3 heuristic

    # Chronicle mode (multiple games)
    python scripts/play_interactive.py --human 1 --num-games 3 --seed 42
"""

import argparse
import logging
import sys

from oath.env.oath_env import OathEnv
from oath.agents.human_agent import HumanAgent
from oath.agents.random_agent import RandomAgent
from oath.agents.heuristic_agent import HeuristicAgent
from oath.display.renderer import render_full_board


AGENT_TYPES = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,
}


def main():
    parser = argparse.ArgumentParser(
        description="Play an interactive Oath game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--human", action="append", type=int, metavar="PLAYER",
                        help="Player index controlled by human (repeatable, 0-5)")
    parser.add_argument("--agent", action="append", nargs=2,
                        metavar=("PLAYER", "TYPE"),
                        help="Set AI agent for player index. TYPE: random, heuristic")
    parser.add_argument("--clockwork-prince", action="store_true",
                        help="Use Clockwork Prince as Chancellor")
    parser.add_argument("--num-players", type=int, default=4,
                        help="Number of players (default: 4)")
    parser.add_argument("--num-games", type=int, default=1,
                        help="Number of games in chronicle (default: 1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--max-iter", type=int, default=10000,
                        help="Max steps per game (default: 10000)")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: WARNING)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname).1s %(name)s: %(message)s",
    )

    human_indices = set(args.human) if args.human else set()

    # Build agents
    agents: dict[int, object] = {}

    # Human agents
    for idx in human_indices:
        if idx >= args.num_players:
            print(f"Error: --human {idx} but only {args.num_players} players", file=sys.stderr)
            sys.exit(1)
        agents[idx] = HumanAgent(player_index=idx, seed=args.seed)

    # Configured AI agents
    if args.agent:
        for player_str, agent_type in args.agent:
            player_idx = int(player_str)
            agent_type = agent_type.lower()
            if agent_type not in AGENT_TYPES:
                print(f"Unknown agent type: {agent_type}. "
                      f"Available: {', '.join(AGENT_TYPES.keys())}",
                      file=sys.stderr)
                sys.exit(1)
            if player_idx in human_indices:
                print(f"Warning: P{player_idx} is human, ignoring --agent", file=sys.stderr)
                continue
            agents[player_idx] = AGENT_TYPES[agent_type](seed=args.seed + player_idx)

    # Fill remaining with RandomAgent
    for i in range(args.num_players):
        if i not in agents:
            agents[i] = RandomAgent(seed=args.seed + i)

    # Create environment
    env = OathEnv(
        num_players=args.num_players,
        clockwork_prince=args.clockwork_prince,
        chronicle_mode=(args.num_games > 1),
        seed=args.seed,
    )

    # Play games
    for game_idx in range(args.num_games):
        print(f"\n{'=' * 60}")
        print(f"  GAME {game_idx + 1} of {args.num_games}")
        print(f"{'=' * 60}")

        env.reset()
        gs = env.game_state

        # Show initial state
        print(f"\nOath: {gs.oath_goal.name}  |  Successor: {gs.successor_goal.name}")
        print(f"Chancellor: P{gs.chancellor_index}")
        for i in range(gs.num_players):
            p = gs.players[i]
            agent_type = type(agents[i]).__name__
            print(f"  P{i}: {p.role.name} ({agent_type})")

        step_count = 0
        for agent_name in env.agent_iter(max_iter=args.max_iter):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                env.step(None)
                step_count += 1
                continue

            player_idx = int(agent_name.split("_")[1])
            agent = agents[player_idx]

            # Provide game state to human agents
            if isinstance(agent, HumanAgent):
                agent.set_game_state(env.game_state)

            action = agent.act(obs)
            env.step(action)
            step_count += 1

        # Game over
        gs = env.game_state
        if gs is not None and gs.winner is not None:
            winner = gs.winner
            winner_role = gs.players[winner].role.name
            win_type = gs.win_type.name if gs.win_type is not None else "UNKNOWN"
            print(f"\n{'=' * 60}")
            print(f"  GAME OVER  |  Round {gs.round_number}")
            print(f"  Winner: P{winner} ({winner_role})")
            print(f"  Win type: {win_type}")
            print(f"  Steps: {step_count}")
            print(f"{'=' * 60}")

            # Show final board for human players
            if human_indices:
                viewer = min(human_indices)
                print(render_full_board(gs, viewer))
        else:
            print("\nGame ended without a winner (max iterations reached).")


if __name__ == "__main__":
    main()

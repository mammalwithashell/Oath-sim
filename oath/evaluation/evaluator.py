"""Chronicle evaluation harness for Oath RL agents.

Runs a sequence of games through the chronicle system, collecting
per-game and per-chronicle statistics to measure agent quality.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

from oath.enums import OathGoal, Role, SuccessorGoal, WinType
from oath.env.oath_env import OathEnv
from oath.agents.random_agent import RandomAgent


@dataclass
class GameResult:
    """Statistics from a single game within a chronicle."""
    game_index: int
    winner: int
    win_type: Optional[WinType]
    winner_role: Role
    oath_goal: OathGoal
    successor_goal: SuccessorGoal
    round_number: int
    num_players: int
    chancellor_index: int
    roles: list[Role]
    sites_ruled: list[int]
    visions_drawn: int
    citizenship_changes: int


@dataclass
class ChronicleResult:
    """Aggregate statistics from a full chronicle sequence."""
    games: list[GameResult]
    seed: int
    agent_configs: dict[int, str] = field(default_factory=dict)

    @property
    def win_counts(self) -> dict[int, int]:
        """Count wins per player index."""
        counts: dict[int, int] = {}
        for g in self.games:
            counts[g.winner] = counts.get(g.winner, 0) + 1
        return counts

    @property
    def win_type_counts(self) -> dict[WinType, int]:
        """Count wins by type."""
        counts: dict[WinType, int] = {}
        for g in self.games:
            if g.win_type is not None:
                counts[g.win_type] = counts.get(g.win_type, 0) + 1
        return counts

    @property
    def oath_goal_sequence(self) -> list[OathGoal]:
        """Sequence of oath goals across the chronicle."""
        return [g.oath_goal for g in self.games]

    @property
    def avg_game_length(self) -> float:
        """Average number of rounds per game."""
        if not self.games:
            return 0.0
        return sum(g.round_number for g in self.games) / len(self.games)

    @property
    def win_rate_by_role(self) -> dict[str, float]:
        """Win rate grouped by the winner's role."""
        role_wins: dict[str, int] = {}
        role_total: dict[str, int] = {}
        for g in self.games:
            role_name = g.winner_role.name
            role_wins[role_name] = role_wins.get(role_name, 0) + 1
        total = len(self.games) if self.games else 1
        return {r: w / total for r, w in role_wins.items()}

    @property
    def chancellor_rotation_count(self) -> int:
        """How many times the Chancellor seat changed player."""
        changes = 0
        for i in range(1, len(self.games)):
            if self.games[i].chancellor_index != self.games[i - 1].chancellor_index:
                changes += 1
        return changes


class ChronicleEvaluator:
    """Runs a chronicle sequence and collects evaluation statistics.

    Args:
        num_players: Number of players (2-6).
        num_games: Number of games in the chronicle sequence.
        agents: Dict mapping player index to agent instance (must have .act(obs)->int).
            Missing indices default to RandomAgent.
        clockwork_prince: If True, Chancellor is auto-played by ClockworkPrinceAgent.
        seed: RNG seed for reproducibility.
        max_iter_per_game: Safety limit on steps per game.
    """

    def __init__(
        self,
        num_players: int = 4,
        num_games: int = 10,
        agents: Optional[dict[int, Any]] = None,
        clockwork_prince: bool = False,
        seed: int = 42,
        max_iter_per_game: int = 5000,
    ):
        self.num_players = num_players
        self.num_games = num_games
        self.agents = agents or {}
        self.clockwork_prince = clockwork_prince
        self.seed = seed
        self.max_iter_per_game = max_iter_per_game

        # Fill missing agent slots with RandomAgent
        self._resolved_agents: dict[int, Any] = {}
        for i in range(num_players):
            if i in self.agents:
                self._resolved_agents[i] = self.agents[i]
            else:
                self._resolved_agents[i] = RandomAgent(seed=seed + i)

    def run(self) -> ChronicleResult:
        """Run a full chronicle sequence and return results."""
        env = OathEnv(
            num_players=self.num_players,
            clockwork_prince=self.clockwork_prince,
            chronicle_mode=True,
            seed=self.seed,
        )

        games: list[GameResult] = []
        for game_idx in range(self.num_games):
            result = self._play_one_game(env, game_idx)
            games.append(result)

        # Build agent config names
        agent_configs = {}
        for idx, agent in self._resolved_agents.items():
            agent_configs[idx] = type(agent).__name__
        if self.clockwork_prince:
            # Chancellor agent is the Clockwork Prince (controlled by env)
            chanc_idx = games[0].chancellor_index if games else 0
            agent_configs[chanc_idx] = "ClockworkPrince"

        return ChronicleResult(
            games=games,
            seed=self.seed,
            agent_configs=agent_configs,
        )

    def _play_one_game(self, env: OathEnv, game_index: int) -> GameResult:
        """Play a single game using configured agents."""
        env.reset()
        gs = env.game_state
        assert gs is not None

        initial_oath_goal = gs.oath_goal
        initial_successor_goal = gs.successor_goal
        chancellor_idx = gs.chancellor_index
        initial_roles = [p.role for p in gs.players]

        # Track citizenship changes
        citizenship_changes = 0
        prev_roles = list(initial_roles)

        step_count = 0
        for agent_name in env.agent_iter(max_iter=self.max_iter_per_game):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                env.step(None)
                step_count += 1
                continue

            player_idx = int(agent_name.split("_")[1])

            # Use configured agent (skip if Clockwork Prince handles Chancellor)
            if self.clockwork_prince and player_idx == chancellor_idx:
                # Clockwork Prince is auto-played by the env
                env.step(None)
            else:
                agent = self._resolved_agents.get(player_idx)
                if agent is not None:
                    action = agent.act(obs)
                    env.step(action)
                else:
                    env.step(None)

            # Check for role changes (citizenship transitions)
            gs = env.game_state
            if gs is not None:
                for i in range(gs.num_players):
                    if i < len(gs.players) and i < len(prev_roles):
                        if gs.players[i].role != prev_roles[i]:
                            citizenship_changes += 1
                            prev_roles[i] = gs.players[i].role

            step_count += 1

        # Extract final game state
        gs = env.game_state
        assert gs is not None

        # Use the winner's role at game end, not at game start
        winner_idx = gs.winner if gs.winner is not None else 0
        winner_role = gs.players[winner_idx].role if gs.winner is not None else Role.CHANCELLOR

        return GameResult(
            game_index=game_index,
            winner=winner_idx,
            win_type=gs.win_type,
            winner_role=winner_role,
            oath_goal=initial_oath_goal,
            successor_goal=initial_successor_goal,
            round_number=gs.round_number,
            num_players=gs.num_players,
            chancellor_index=chancellor_idx,
            roles=[p.role for p in gs.players],
            sites_ruled=[gs.count_sites_ruled(i) for i in range(gs.num_players)],
            visions_drawn=gs.visions_drawn,
            citizenship_changes=citizenship_changes,
        )

    @staticmethod
    def summarize(result: ChronicleResult) -> str:
        """Return a human-readable summary of a chronicle sequence."""
        lines = []
        lines.append(f"=== Chronicle Summary (seed={result.seed}) ===")
        lines.append(f"Games: {len(result.games)}  |  Avg rounds: {result.avg_game_length:.1f}")
        lines.append("")

        # Per-game table
        lines.append(f"{'Game':>4}  {'Winner':>6}  {'Role':<12}  {'Win Type':<18}  "
                      f"{'Oath Goal':<12}  {'Chanc':>5}  {'Rounds':>6}")
        lines.append("-" * 75)
        for g in result.games:
            win_type_name = g.win_type.name if g.win_type is not None else "UNKNOWN"
            lines.append(
                f"{g.game_index:>4}  "
                f"P{g.winner:>4}  "
                f"{g.winner_role.name:<12}  "
                f"{win_type_name:<18}  "
                f"{g.oath_goal.name:<12}  "
                f"P{g.chancellor_index:>4}  "
                f"{g.round_number:>6}"
            )

        lines.append("")

        # Win counts
        lines.append("--- Win Counts by Player ---")
        for player_idx, count in sorted(result.win_counts.items()):
            agent_name = result.agent_configs.get(player_idx, "Unknown")
            lines.append(f"  Player {player_idx} ({agent_name}): {count} wins")

        # Win types
        lines.append("")
        lines.append("--- Win Types ---")
        for wt, count in sorted(result.win_type_counts.items(), key=lambda x: x[0]):
            lines.append(f"  {wt.name}: {count}")

        # Win rate by role
        lines.append("")
        lines.append("--- Win Rate by Role ---")
        for role_name, rate in sorted(result.win_rate_by_role.items()):
            lines.append(f"  {role_name}: {rate:.1%}")

        # Oath goal sequence
        lines.append("")
        oath_seq = " -> ".join(g.name for g in result.oath_goal_sequence)
        lines.append(f"Oath sequence: {oath_seq}")

        # Chancellor rotation
        lines.append(f"Chancellor rotations: {result.chancellor_rotation_count}")

        return "\n".join(lines)

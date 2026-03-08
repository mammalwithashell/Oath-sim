"""Game session management for the web API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from oath.agents.heuristic_agent import HeuristicAgent
from oath.agents.random_agent import RandomAgent
from oath.api.serializers import (
    serialize_action_highlights,
    serialize_game_state,
    serialize_legal_actions,
)
from oath.display.renderer import describe_action
from oath.env.oath_env import OathEnv


AGENT_TYPES = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,
}


@dataclass
class GameSession:
    """A single active game."""
    game_id: str
    env: OathEnv
    agents: dict[int, object]
    human_players: set[int]
    action_log: list[dict] = field(default_factory=list)
    pending_ai_actions: list[dict] = field(default_factory=list)
    _iter: object = field(default=None, repr=False)
    _current_agent: Optional[str] = None
    _game_started: bool = False

    def start(self) -> None:
        """Reset env and advance through AI turns to first human turn."""
        self.env.reset()
        self._iter = self.env.agent_iter(max_iter=50000)
        self._game_started = True
        self.pending_ai_actions = []
        self.action_log = []
        self._advance_to_human()

    def _advance_to_human(self) -> None:
        """Run AI turns until it's a human player's turn or game over."""
        for agent_name in self._iter:
            obs, reward, terminated, truncated, info = self.env.last()

            if terminated or truncated:
                self.env.step(None)
                continue

            player_idx = int(agent_name.split("_")[1])

            if player_idx in self.human_players:
                self._current_agent = agent_name
                return

            # AI turn
            agent = self.agents.get(player_idx)
            if agent is None:
                self.env.step(None)
                continue

            action = agent.act(obs)
            gs = self.env.game_state
            desc = describe_action(action, gs, player_idx)
            role = gs.players[player_idx].role.name

            highlights = serialize_action_highlights(action, gs, player_idx)

            log_entry = {
                "player": player_idx,
                "role": role,
                "action_id": action,
                "description": desc,
                "highlights": highlights,
            }
            self.action_log.append(log_entry)
            self.pending_ai_actions.append(log_entry)

            self.env.step(action)

        # Game over
        self._current_agent = None

    def apply_human_action(self, action_id: int) -> None:
        """Apply a human player's action, then advance to next human turn."""
        gs = self.env.game_state
        player_idx = gs.current_player_index
        desc = describe_action(action_id, gs, player_idx)
        role = gs.players[player_idx].role.name

        self.action_log.append({
            "player": player_idx,
            "role": role,
            "action_id": action_id,
            "description": desc,
            "is_human": True,
        })

        self.env.step(action_id)
        self.pending_ai_actions = []
        self._advance_to_human()

    def get_state_response(self) -> dict:
        """Build the full API response for the current state."""
        gs = self.env.game_state
        viewer = min(self.human_players) if self.human_players else 0

        obs, _, terminated, _, info = self.env.last()

        is_human_turn = (
            self._current_agent is not None
            and not gs.is_game_over
            and int(self._current_agent.split("_")[1]) in self.human_players
        )

        legal_actions = []
        human_player_index = None
        if is_human_turn and obs is not None:
            human_player_index = int(self._current_agent.split("_")[1])
            legal_actions = serialize_legal_actions(
                gs, human_player_index, obs["action_mask"]
            )

        return {
            "game_id": self.game_id,
            "game_state": serialize_game_state(gs, viewer),
            "is_human_turn": is_human_turn,
            "human_player_index": human_player_index,
            "legal_actions": legal_actions,
            "ai_actions": list(self.pending_ai_actions),
            "action_log": list(self.action_log),
        }


class GameManager:
    """Manages active game sessions."""

    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    def create_game(
        self,
        num_players: int = 4,
        human_players: list[int] | None = None,
        agent_config: dict[str, str] | None = None,
        clockwork_prince: bool = False,
        seed: int | None = None,
    ) -> GameSession:
        """Create and start a new game session."""
        game_id = uuid.uuid4().hex[:12]
        human_set = set(human_players or [0])
        agent_config = agent_config or {}

        env = OathEnv(
            num_players=num_players,
            clockwork_prince=clockwork_prince,
            seed=seed,
        )

        agents: dict[int, object] = {}
        for i in range(num_players):
            if i in human_set:
                continue
            if clockwork_prince and i == 0:
                continue
            agent_type = agent_config.get(str(i), "random")
            cls = AGENT_TYPES.get(agent_type, RandomAgent)
            agents[i] = cls(seed=(seed or 42) + i)

        session = GameSession(
            game_id=game_id,
            env=env,
            agents=agents,
            human_players=human_set,
        )
        session.start()
        self.sessions[game_id] = session
        return session

    def get_session(self, game_id: str) -> Optional[GameSession]:
        return self.sessions.get(game_id)

    def delete_game(self, game_id: str) -> bool:
        return self.sessions.pop(game_id, None) is not None

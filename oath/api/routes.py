"""FastAPI route handlers."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from oath.api.game_manager import GameManager

router = APIRouter(prefix="/api")
game_manager = GameManager()


class CreateGameRequest(BaseModel):
    num_players: int = 4
    human_players: list[int] = [0]
    agents: dict[str, str] = {}
    clockwork_prince: bool = False
    seed: Optional[int] = None


class ActionRequest(BaseModel):
    action_id: int


@router.post("/games")
def create_game(req: CreateGameRequest):
    if not (2 <= req.num_players <= 6):
        raise HTTPException(400, "num_players must be 2-6")
    for hp in req.human_players:
        if hp < 0 or hp >= req.num_players:
            raise HTTPException(400, f"human_player {hp} out of range")
    if req.clockwork_prince and 0 in req.human_players:
        raise HTTPException(400, "Cannot be human and clockwork prince (player 0)")

    session = game_manager.create_game(
        num_players=req.num_players,
        human_players=req.human_players,
        agent_config=req.agents,
        clockwork_prince=req.clockwork_prince,
        seed=req.seed,
    )
    return session.get_state_response()


@router.get("/games/{game_id}/state")
def get_state(game_id: str):
    session = game_manager.get_session(game_id)
    if session is None:
        raise HTTPException(404, "Game not found")
    return session.get_state_response()


@router.post("/games/{game_id}/action")
def take_action(game_id: str, req: ActionRequest):
    session = game_manager.get_session(game_id)
    if session is None:
        raise HTTPException(404, "Game not found")

    gs = session.env.game_state
    if gs.is_game_over:
        raise HTTPException(400, "Game is already over")

    if not session._current_agent:
        raise HTTPException(400, "Not a human player's turn")

    player_idx = int(session._current_agent.split("_")[1])
    if player_idx not in session.human_players:
        raise HTTPException(400, "Not a human player's turn")

    # Validate action is legal
    obs, _, _, _, _ = session.env.last()
    if obs is not None and obs["action_mask"][req.action_id] < 0.5:
        raise HTTPException(400, f"Action {req.action_id} is not legal")

    session.apply_human_action(req.action_id)
    return session.get_state_response()


@router.delete("/games/{game_id}")
def delete_game(game_id: str):
    if not game_manager.delete_game(game_id):
        raise HTTPException(404, "Game not found")
    return {"status": "deleted"}

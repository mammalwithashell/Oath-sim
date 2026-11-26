"""FastAPI WebSocket + REST server for Human-vs-AI Oath, Scenario Staging, Chronicle Import/Export, and Replay Viewer."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import oath_rs
from rl.model import OathLSTMNet

MODELS_DIR = Path("models")
REPLAYS_DIR = Path("replays")
REPLAYS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Oath-sim Rust + RL + Replay Server", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache loaded PyTorch models by checkpoint path
_MODEL_CACHE: dict[str, OathLSTMNet] = {}


def _load_lstm_model(checkpoint_path: str | None) -> OathLSTMNet | None:
    if not checkpoint_path:
        # Fallback to best or latest checkpoint
        for cand in [
            MODELS_DIR / "oath_lstm_250k_best.pt",
            MODELS_DIR / "oath_lstm_latest.pt",
        ]:
            if cand.exists():
                checkpoint_path = str(cand)
                break
    if not checkpoint_path:
        return None
    path = Path(checkpoint_path)
    if not path.exists():
        return None
    key = str(path.resolve())
    if key not in _MODEL_CACHE:
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        model = OathLSTMNet(
            obs_flat_size=ckpt.get("obs_flat_size", oath_rs.OBS_FLAT_SIZE),
            num_card_slots=ckpt.get("num_card_slots", oath_rs.OBS_CARD_IDS_SIZE),
            num_actions=ckpt.get("num_actions", oath_rs.NUM_ACTIONS),
            hidden_size=ckpt.get("hidden_size", 256),
        )
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        _MODEL_CACHE[key] = model
    return _MODEL_CACHE[key]


def _enrich_state(raw: dict[str, Any]) -> dict[str, Any]:
    card_cache: dict[int, dict[str, Any]] = {}

    def card_meta(cid: int) -> dict[str, Any] | None:
        if cid == 0:
            return None
        if cid not in card_cache:
            i, name, suit, text = oath_rs.card_info(cid)
            card_cache[cid] = {"id": i, "name": name, "suit": suit, "text": text}
        return card_cache[cid]

    for s in raw["sites"]:
        s["site_meta"] = card_meta(s["site_id"])
        s["card_metas"] = [card_meta(c) for c in s["cards"]]
        s["relic_metas"] = [card_meta(r) for r in s["relics"]]
    for p in raw["players"][: raw["num_players"]]:
        p["adviser_metas"] = [card_meta(c) for c in p["advisers"]]
        p["relic_metas"] = [card_meta(r) for r in p["relics"]]
    return raw


def _categorize_action(action_id: int) -> str:
    if 0 <= action_id <= 7:
        return "TRAVEL"
    if 8 <= action_id <= 9:
        return "SEARCH"
    if 10 <= action_id <= 18:
        return "MUSTER_TRADE"
    if 19 <= action_id <= 23:
        return "RECOVER"
    if 24 <= action_id <= 29:
        return "CAMPAIGN"
    if 30 <= action_id <= 63:
        return "MINOR"
    if action_id == 64:
        return "END_TURN"
    if 155 <= action_id <= 185:
        return "DEAL"
    if 186 <= action_id <= 214:
        return "TALK"
    return "CHOICE"


class CreateGameRequest(BaseModel):
    num_players: int = 4
    seats: list[str] = ["heuristic", "human", "heuristic", "mcts"]
    seat_checkpoints: list[str | None] = []
    seed: int = 42
    first_game: bool = True
    oath_goal: int | None = None
    chronicle_enabled: bool = False
    checkpoint_path: str | None = None
    staged_sites: list[int] | None = None
    staged_reliquary: list[int] | None = None
    staged_chancellor_relics: list[int] | None = None
    chronicle_json: str | None = None
    state_json: str | None = None


class SimulateReplayRequest(BaseModel):
    name: str | None = None
    num_players: int = 4
    num_chronicles: int = 3
    seats: list[str] = ["lstm", "lstm", "heuristic", "mcts"]
    seat_checkpoints: list[str | None] = []
    seed: int = 42
    first_game: bool = True
    oath_goal: int | None = 0
    staged_sites: list[int] | None = None
    staged_reliquary: list[int] | None = None
    staged_chancellor_relics: list[int] | None = None
    chronicle_json: str | None = None


class TakeoverRequest(BaseModel):
    chronicle_index: int = 0
    frame_index: int = 0
    seats: list[str] = ["lstm", "human", "heuristic", "mcts"]
    seat_checkpoints: list[str | None] = []


class ActionRequest(BaseModel):
    action_id: int


def _pick_ai_action(
    env: oath_rs.OathEnv,
    player: int,
    seat: str,
    ckpt_path: str | None,
    lstm_states: dict[int, tuple[torch.Tensor, torch.Tensor]],
    step_seed: int,
) -> tuple[int, dict[str, Any] | None]:
    if seat == "random":
        return int(env.random_action(step_seed)), None
    if seat == "mcts":
        best, policy, root_vals = env.mcts_search(
            num_determinizations=2, sims_per_det=24, seed=step_seed
        )
        top_idx = np.argsort(policy)[::-1][:5]
        legal_map = dict(env.legal_actions_described())
        insp = {
            "player": player,
            "agent": "IS-MCTS (Rust)",
            "win_probs": [round(float(v), 3) for v in root_vals[: env.num_players()]],
            "top_actions": [
                {
                    "action_id": int(a),
                    "description": legal_map.get(int(a), f"Action {a}"),
                    "prob": round(float(policy[a]), 3),
                }
                for a in top_idx
                if policy[a] > 0.001
            ],
        }
        return int(best), insp
    if seat == "lstm":
        model = _load_lstm_model(ckpt_path)
        if model is not None:
            obs_flat, card_ids, mask, _ = env.observe(player)
            t_obs = torch.from_numpy(obs_flat).unsqueeze(0)
            t_cids = torch.from_numpy(card_ids).unsqueeze(0)
            t_mask = torch.from_numpy(mask.astype(np.float32)).unsqueeze(0)
            st = lstm_states.get(player)
            act, _, _, probs, mp_vals, next_st = model.act(t_obs, t_cids, t_mask, st)
            lstm_states[player] = next_st
            p_np = probs.squeeze(0).numpy()
            top_idx = np.argsort(p_np)[::-1][:5]
            legal_map = dict(env.legal_actions_described())
            label = Path(ckpt_path).name if ckpt_path else "OathLSTMNet"
            insp = {
                "player": player,
                "agent": f"LSTM ({label})",
                "win_probs": [
                    round(float(v), 3)
                    for v in mp_vals.squeeze(0).numpy()[: env.num_players()]
                ],
                "top_actions": [
                    {
                        "action_id": int(a),
                        "description": legal_map.get(int(a), f"Action {a}"),
                        "prob": round(float(p_np[a]), 3),
                    }
                    for a in top_idx
                    if p_np[a] > 0.001
                ],
            }
            return int(act.item()), insp
    return int(env.heuristic_action(step_seed)), None


def _build_env_from_config(
    num_players: int,
    seed: int,
    first_game: bool,
    oath_goal: int | None,
    chronicle_enabled: bool,
    staged_sites: list[int] | None,
    staged_reliquary: list[int] | None,
    staged_chancellor_relics: list[int] | None,
    chronicle_json: str | None,
    state_json: str | None = None,
) -> oath_rs.OathEnv:
    env = oath_rs.OathEnv(
        num_players=num_players,
        seed=seed,
        first_game=first_game,
        oath_goal=oath_goal,
        chronicle_enabled=chronicle_enabled,
    )
    if state_json:
        env.load_state_json(state_json)
        return env
    if chronicle_json:
        env.import_chronicle_json(chronicle_json, seed=seed)
    if any(x is not None for x in (staged_sites, staged_reliquary, staged_chancellor_relics)):
        env.stage_scenario(
            sites=staged_sites,
            reliquary=staged_reliquary,
            chancellor_relics=staged_chancellor_relics,
            oath_goal=oath_goal,
        )
    return env


class GameSession:
    def __init__(self, game_id: str, req: CreateGameRequest) -> None:
        self.game_id = game_id
        self.seats = list(req.seats[: req.num_players])
        while len(self.seats) < req.num_players:
            self.seats.append("heuristic")
        self.seat_checkpoints: list[str | None] = []
        for i in range(req.num_players):
            cp = req.seat_checkpoints[i] if i < len(req.seat_checkpoints) else req.checkpoint_path
            self.seat_checkpoints.append(cp)

        self.env = _build_env_from_config(
            num_players=req.num_players,
            seed=req.seed,
            first_game=req.first_game,
            oath_goal=req.oath_goal,
            chronicle_enabled=req.chronicle_enabled,
            staged_sites=req.staged_sites,
            staged_reliquary=req.staged_reliquary,
            staged_chancellor_relics=req.staged_chancellor_relics,
            chronicle_json=req.chronicle_json,
            state_json=req.state_json,
        )
        self.lstm_states: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.step_seed = req.seed + 1000
        self.action_log: list[dict[str, Any]] = []
        self.last_ai_inspector: dict[str, Any] | None = None

    def is_human_seat(self, player: int | None) -> bool:
        return player is not None and 0 <= player < len(self.seats) and self.seats[player] == "human"

    def advance_until_human(self) -> list[dict[str, Any]]:
        recent: list[dict[str, Any]] = []
        guard = 0
        while not self.env.is_game_over() and guard < 200:
            acting = self.env.acting_player()
            if self.is_human_seat(acting):
                break
            assert acting is not None
            self.step_seed += 1
            legal_map = dict(self.env.legal_actions_described())
            act_id, insp = _pick_ai_action(
                self.env,
                acting,
                self.seats[acting],
                self.seat_checkpoints[acting],
                self.lstm_states,
                self.step_seed,
            )
            if insp is not None:
                self.last_ai_inspector = insp
            desc = legal_map.get(act_id, f"Action {act_id}")
            self.env.step(act_id)
            entry = {
                "player": acting,
                "seat": self.seats[acting],
                "action_id": act_id,
                "description": desc,
            }
            self.action_log.append(entry)
            recent.append(entry)
            guard += 1
        return recent

    def apply_human_action(self, action_id: int) -> list[dict[str, Any]]:
        acting = self.env.acting_player()
        legal_map = dict(self.env.legal_actions_described())
        desc = legal_map.get(action_id, f"Action {action_id}")
        self.env.step(action_id)
        self.action_log.append(
            {
                "player": acting,
                "seat": "human",
                "action_id": action_id,
                "description": desc,
            }
        )
        return self.advance_until_human()

    def payload(self, ai_actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        raw = _enrich_state(json.loads(self.env.state_json()))
        acting = self.env.acting_player()
        legal_actions = [
            {
                "action_id": aid,
                "category": _categorize_action(aid),
                "description": desc,
            }
            for aid, desc in self.env.legal_actions_described()
        ]
        return {
            "game_id": self.game_id,
            "seats": self.seats,
            "seat_checkpoints": self.seat_checkpoints,
            "acting_player": acting,
            "is_human_turn": self.is_human_seat(acting),
            "state": raw,
            "legal_actions": legal_actions,
            "ai_actions": ai_actions or [],
            "action_log": self.action_log[-60:],
            "ai_inspector": self.last_ai_inspector,
        }


SESSIONS: dict[str, GameSession] = {}


# ── Catalog & Models Discovery ────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "engine": "oath_rs",
        "num_cards": oath_rs.NUM_CARDS,
        "num_actions": oath_rs.NUM_ACTIONS,
    }


@app.get("/api/models")
def list_models() -> dict[str, Any]:
    models = []
    if MODELS_DIR.exists():
        for p in sorted(MODELS_DIR.glob("*.pt")):
            models.append({"name": p.name, "path": str(p)})
    return {"models": models}


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    sites = []
    for sid in range(237, 260):
        i, name, suit, text = oath_rs.card_info(sid)
        sites.append({"id": i, "name": name, "suit": suit, "text": text})
    relics = []
    for rid in range(211, 231):
        i, name, suit, text = oath_rs.card_info(rid)
        relics.append({"id": i, "name": name, "suit": suit, "text": text})
    return {"sites": sites, "relics": relics}


# ── Live Game & Chronicle Export Endpoints ────────────────────────────────

@app.post("/api/games")
def create_game(req: CreateGameRequest) -> dict[str, Any]:
    gid = uuid.uuid4().hex[:8]
    try:
        sess = GameSession(gid, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ai_acts = sess.advance_until_human()
    SESSIONS[gid] = sess
    return sess.payload(ai_acts)


@app.get("/api/games/{game_id}/state")
def get_state(game_id: str) -> dict[str, Any]:
    sess = SESSIONS.get(game_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Game not found")
    return sess.payload()


@app.post("/api/games/{game_id}/action")
def post_action(game_id: str, req: ActionRequest) -> dict[str, Any]:
    sess = SESSIONS.get(game_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        ai_acts = sess.apply_human_action(req.action_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return sess.payload(ai_acts)


@app.get("/api/games/{game_id}/chronicle/export")
def export_chronicle(game_id: str) -> dict[str, Any]:
    sess = SESSIONS.get(game_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Game not found")
    ch_json = sess.env.export_chronicle_json()
    return {"game_id": game_id, "chronicle_json": ch_json}


@app.websocket("/ws/games/{game_id}")
async def ws_game(websocket: WebSocket, game_id: str) -> None:
    await websocket.accept()
    sess = SESSIONS.get(game_id)
    if not sess:
        await websocket.send_json({"error": "Game not found"})
        await websocket.close()
        return
    await websocket.send_json(sess.payload())
    try:
        while True:
            msg = await websocket.receive_json()
            if "action_id" in msg:
                try:
                    ai_acts = sess.apply_human_action(int(msg["action_id"]))
                    await websocket.send_json(sess.payload(ai_acts))
                except ValueError as exc:
                    await websocket.send_json({"error": str(exc)})
    except WebSocketDisconnect:
        pass


# ── AI-vs-AI Simulation, Replay Viewer & Drop-In Takeover ─────────────────

@app.post("/api/replays/simulate")
def simulate_replay(req: SimulateReplayRequest) -> dict[str, Any]:
    num_chronicles = max(1, min(req.num_chronicles, 50))
    seats = [s if s != "human" else "heuristic" for s in req.seats[: req.num_players]]
    while len(seats) < req.num_players:
        seats.append("heuristic")
    seat_ckpts = [
        req.seat_checkpoints[i] if i < len(req.seat_checkpoints) else None
        for i in range(req.num_players)
    ]

    try:
        env = _build_env_from_config(
            num_players=req.num_players,
            seed=req.seed,
            first_game=req.first_game,
            oath_goal=req.oath_goal,
            chronicle_enabled=True,
            staged_sites=req.staged_sites,
            staged_reliquary=req.staged_reliquary,
            staged_chancellor_relics=req.staged_chancellor_relics,
            chronicle_json=req.chronicle_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    replay_id = f"rep_{uuid.uuid4().hex[:8]}"
    chronicles: list[dict[str, Any]] = []
    step_seed = req.seed + 5000

    for c_idx in range(num_chronicles):
        if c_idx > 0:
            env.reset()
        lstm_states: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        frames: list[dict[str, Any]] = []
        raw_json_str = env.state_json()
        frames.append(
            {
                "step": 0,
                "actor": env.acting_player(),
                "action_id": None,
                "description": f"Start of Chronicle {c_idx + 1}",
                "ai_inspector": None,
                "raw_state_json": raw_json_str,
                "state": _enrich_state(json.loads(raw_json_str)),
            }
        )
        step_i = 0
        while not env.is_game_over() and step_i < 2000:
            ap = env.acting_player()
            assert ap is not None
            step_seed += 1
            legal_map = dict(env.legal_actions_described())
            act_id, insp = _pick_ai_action(
                env, ap, seats[ap], seat_ckpts[ap], lstm_states, step_seed
            )
            desc = legal_map.get(act_id, f"Action {act_id}")
            env.step(act_id)
            step_i += 1
            raw_str = env.state_json()
            frames.append(
                {
                    "step": step_i,
                    "actor": ap,
                    "action_id": act_id,
                    "description": desc,
                    "ai_inspector": insp,
                    "raw_state_json": raw_str,
                    "state": _enrich_state(json.loads(raw_str)),
                }
            )
        end_st = frames[-1]["state"]
        ch_export = env.export_chronicle_json()
        chronicles.append(
            {
                "chronicle_number": c_idx + 1,
                "oath_goal": frames[0]["state"]["oath_goal"],
                "winner": end_st["winner"],
                "win_type": end_st["win_type"],
                "vowed_oath": end_st["vowed_oath"],
                "rounds": end_st["round_number"],
                "num_frames": len(frames),
                "chronicle_json": ch_export,
                "frames": frames,
            }
        )

    replay_doc = {
        "replay_id": replay_id,
        "name": req.name or f"{num_chronicles}-Chronicle Match ({', '.join(seats)})",
        "created_at": int(time.time()),
        "num_players": req.num_players,
        "seats": seats,
        "seat_checkpoints": seat_ckpts,
        "num_chronicles": num_chronicles,
        "chronicles": chronicles,
    }
    (REPLAYS_DIR / f"{replay_id}.json").write_text(json.dumps(replay_doc))
    return {
        "replay_id": replay_id,
        "name": replay_doc["name"],
        "num_chronicles": num_chronicles,
        "summary": [
            {
                "chronicle_number": c["chronicle_number"],
                "oath_goal": c["oath_goal"],
                "winner": c["winner"],
                "win_type": c["win_type"],
                "vowed_oath": c["vowed_oath"],
                "rounds": c["rounds"],
                "num_frames": c["num_frames"],
            }
            for c in chronicles
        ],
    }


@app.get("/api/replays")
def list_replays() -> dict[str, Any]:
    items = []
    for p in sorted(REPLAYS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            doc = json.loads(p.read_text())
            items.append(
                {
                    "replay_id": doc["replay_id"],
                    "name": doc["name"],
                    "created_at": doc.get("created_at", 0),
                    "num_players": doc["num_players"],
                    "seats": doc["seats"],
                    "num_chronicles": doc["num_chronicles"],
                }
            )
        except Exception:
            continue
    return {"replays": items}


@app.get("/api/replays/{replay_id}")
def get_replay(replay_id: str) -> dict[str, Any]:
    path = REPLAYS_DIR / f"{replay_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Replay not found")
    return json.loads(path.read_text())


@app.post("/api/replays/{replay_id}/takeover")
def takeover_from_replay(replay_id: str, req: TakeoverRequest) -> dict[str, Any]:
    """Drop in and play live from ANY frame of a saved replay!"""
    path = REPLAYS_DIR / f"{replay_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Replay not found")
    doc = json.loads(path.read_text())
    if req.chronicle_index < 0 or req.chronicle_index >= len(doc["chronicles"]):
        raise HTTPException(status_code=400, detail="Invalid chronicle_index")
    ch = doc["chronicles"][req.chronicle_index]
    if req.frame_index < 0 or req.frame_index >= len(ch["frames"]):
        raise HTTPException(status_code=400, detail="Invalid frame_index")

    raw_state_json = ch["frames"][req.frame_index]["raw_state_json"]
    create_req = CreateGameRequest(
        num_players=doc["num_players"],
        seats=req.seats,
        seat_checkpoints=req.seat_checkpoints or doc.get("seat_checkpoints", []),
        seed=42,
        chronicle_enabled=True,
        state_json=raw_state_json,
    )
    gid = uuid.uuid4().hex[:8]
    sess = GameSession(gid, create_req)
    ai_acts = sess.advance_until_human()
    SESSIONS[gid] = sess
    return sess.payload(ai_acts)

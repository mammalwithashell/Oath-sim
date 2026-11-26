"""End-to-end integration tests for Rust oath_rs, PyTorch OathLSTMNet, and FastAPI WebSocket server."""
from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

import oath_rs
from server.app import app


def test_oath_rs_single_env_clone_determinize_and_mcts():
    env = oath_rs.OathEnv(num_players=4, seed=42, first_game=True)
    assert oath_rs.NUM_CARDS == 259
    assert oath_rs.NUM_ACTIONS == 216
    assert oath_rs.OBS_FLAT_SIZE == 1024

    obs, cids, mask, ap = env.observe()
    assert obs.shape == (1024,)
    assert cids.shape == (64,)
    assert mask.shape == (216,)
    assert np.all(np.isfinite(obs))
    assert mask.sum() > 0

    cloned = env.clone_env()
    det = env.determinize(1, 99)
    assert cloned.state_json() == env.state_json()
    assert det.num_players() == 4

    best, policy, vals = env.mcts_search(num_determinizations=2, sims_per_det=16, seed=7)
    assert mask[best] == 1
    assert abs(float(policy.sum()) - 1.0) < 1e-4
    assert vals.shape == (6,)


def test_oath_rs_vec_env():
    vec = oath_rs.VecOathEnv(num_envs=8, num_players=4, base_seed=10, single_agent_player=1)
    obs, cids, mask, ap = vec.observe_all()
    assert obs.shape == (8, 1024)
    assert cids.shape == (8, 64)
    assert mask.shape == (8, 216)

    for _ in range(10):
        acts = np.argmax(mask, axis=1).astype(np.uint16)
        obs, cids, mask, rew, dones, ap, winners = vec.step_all(acts)
        assert rew.shape == (8,)
        assert dones.shape == (8,)
        assert winners.shape == (8,)


def test_server_rest_and_websocket_human_vs_lstm_and_mcts():
    client = TestClient(app)

    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["num_cards"] == 259

    # Create 4-player game: Chancellor=MCTS, P1=Human, P2=LSTM, P3=Heuristic
    res = client.post(
        "/api/games",
        json={
            "num_players": 4,
            "seats": ["mcts", "human", "lstm", "heuristic"],
            "seed": 42,
            "first_game": True,
            "oath_goal": 0,
            "chronicle_enabled": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    gid = data["game_id"]
    assert data["is_human_turn"] is True or data["state"]["is_game_over"]
    assert len(data["legal_actions"]) > 0
    assert data["ai_inspector"] is not None

    # Play a turn via WebSocket
    with client.websocket_connect(f"/ws/games/{gid}") as ws:
        init_msg = ws.receive_json()
        assert init_msg["game_id"] == gid
        if init_msg["is_human_turn"] and init_msg["legal_actions"]:
            # Pick a Table Talk or End Turn action
            aid = init_msg["legal_actions"][-1]["action_id"]
            ws.send_json({"action_id": aid})
            next_msg = ws.receive_json()
            assert "state" in next_msg
            assert len(next_msg["action_log"]) > len(init_msg["action_log"])


def test_scenario_staging_chronicle_export_import_and_replay_takeover():
    client = TestClient(app)

    # 1. Catalog & Models endpoints
    cat = client.get("/api/catalog").json()
    assert len(cat["sites"]) == 23
    assert len(cat["relics"]) == 20
    mods = client.get("/api/models").json()
    assert len(mods["models"]) >= 1

    # 2. Create staged game with custom sites, Reliquary, and Chancellor relics
    res = client.post(
        "/api/games",
        json={
            "num_players": 4,
            "seats": ["human", "heuristic", "heuristic", "heuristic"],
            "seed": 77,
            "oath_goal": 2,  # Devotion
            "chronicle_enabled": True,
            "staged_sites": [245, 255, 250, 242, 248, 254, 244, 258],
            "staged_reliquary": [211, 212, 213, 214],
            "staged_chancellor_relics": [227, 226],
        },
    )
    assert res.status_code == 200
    gdata = res.json()
    assert gdata["state"]["oath_goal"] == "Devotion"
    assert gdata["state"]["sites"][0]["site_id"] == 245  # The Tribunal
    assert 227 in gdata["state"]["players"][0]["relics"]  # Map

    # 3. Export Chronicle JSON & re-import it into a new game
    exp = client.get(f"/api/games/{gdata['game_id']}/chronicle/export")
    assert exp.status_code == 200
    ch_json = exp.json()["chronicle_json"]
    imp = client.post(
        "/api/games",
        json={
            "num_players": 4,
            "seats": ["human", "heuristic", "heuristic", "heuristic"],
            "seed": 88,
            "chronicle_enabled": True,
            "chronicle_json": ch_json,
        },
    )
    assert imp.status_code == 200

    # 4. Simulate a 2-Chronicle AI-vs-AI replay (LSTM vs Heuristic)
    sim = client.post(
        "/api/replays/simulate",
        json={
            "name": "Test 2-Chronicle Replay",
            "num_players": 4,
            "num_chronicles": 2,
            "seats": ["lstm", "heuristic", "heuristic", "heuristic"],
            "seed": 123,
            "oath_goal": 0,
        },
    )
    assert sim.status_code == 200
    rep_id = sim.json()["replay_id"]
    assert len(sim.json()["summary"]) == 2

    # 5. Fetch replay & Drop-In Takeover from Chronicle 1, Frame 5 as Human P1
    rep = client.get(f"/api/replays/{rep_id}").json()
    assert len(rep["chronicles"]) == 2
    assert len(rep["chronicles"][0]["frames"]) > 5

    tk = client.post(
        f"/api/replays/{rep_id}/takeover",
        json={
            "chronicle_index": 0,
            "frame_index": 5,
            "seats": ["lstm", "human", "heuristic", "heuristic"],
        },
    )
    assert tk.status_code == 200
    tk_data = tk.json()
    assert tk_data["seats"][1] == "human"
    assert tk_data["is_human_turn"] is True or tk_data["state"]["is_game_over"]


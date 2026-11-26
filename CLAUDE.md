# CLAUDE.md

## Project Overview

Oath-sim is a high-throughput, rules-faithful reinforcement learning simulator and playable web UI for **Oath: Chronicles of Empire and Exile**, built with a **Rust core engine** (`oath-core`, `oath-mcts`, `oath-py`), **PyTorch LSTM RL** (`rl/`), a **FastAPI WebSocket server** (`server/`), and a **React + TypeScript + Tailwind UI** (`frontend/`).

## Quick Reference

```bash
# Run Rust engine & IS-MCTS tests
cargo test -p oath-core -p oath-mcts --release

# Build & install the Python extension (oath_rs)
maturin build --release -m crates/oath-py/Cargo.toml
pip install --force-reinstall --no-deps target/wheels/oath_rl-*.whl

# Run Python & Server integration tests
PYTHONPATH=. pytest -v

# Profile Rust vs PyTorch training throughput
PYTHONPATH=. python3 rl/profile_training.py

# Train RecurrentPPO (LSTM) with BC warm-start & unlimited Chronicles
PYTHONPATH=. python3 rl/train_lstm.py \
  --total-steps 2000000 --num-envs 64 --rollout-steps 64 --hidden-size 256 \
  --curriculum --chronicle --chronicle-max-length 0 \
  --eval-every 25 --saga-games 20 --save models/oath_lstm_2m.pt

# Start the Human-vs-AI & Replay Lab server + frontend
PYTHONPATH=. uvicorn server.app:app --reload --port 8000
npm --prefix frontend run dev
```

## Project Structure

```
crates/
  oath-core/      # Pure Rust Oath engine (259 cards, deals, Tribunal contracts, table talk, Chronicle, VecOathEnv)
  oath-mcts/      # Parallel Determinized IS-MCTS (AlphaZero PUCT) with multi-player value vectors
  oath-py/        # PyO3 + rust-numpy bindings exposing `oath_rs`
data/             # Audited `cards_manifest.json` (259 playable cards OATH-001..259)
rl/               # PyTorch `OathLSTMNet`, RecurrentPPO + BC trainer (`train_lstm.py`), profiler
server/           # FastAPI REST + WebSocket server (Live Play, Scenario Stager, Chronicle Export/Import, Replay Lab)
frontend/         # Vite + React + TypeScript + Tailwind UI (Setup/Stager, Board, Replay Viewer + Drop-In Takeover)
tests/            # Python/Server integration tests
docs/             # Law of Oath rule summaries
```

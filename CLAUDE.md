# CLAUDE.md

## Project Overview

Oath-sim is a reinforcement learning environment for the board game **Oath: Chronicles of Empire and Exile**. It provides a PettingZoo-compatible multi-agent environment with 119 discrete actions, observation encoding, reward shaping, and several AI agents.

## Quick Reference

```bash
# Install (dev mode)
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_actions.py

# Run specific test class
pytest tests/test_actions.py::TestTravel

# Play interactive game
python scripts/play_interactive.py --human 1

# Evaluate chronicle win rates
python scripts/evaluate_chronicle.py --num-games 10 --seed 42
```

## Project Structure

```
oath/
  agents/         # AI agents: RandomAgent, HeuristicAgent, ClockworkPrinceAgent, HumanAgent
  cards/          # Card database (230 cards) and effect implementations
    effects/      # Per-card effect modules
  display/        # Board state renderer for CLI display
  engine/         # Core game logic: actions, campaigns, win conditions, game loop
  env/            # PettingZoo AEC environment: action_decoder, observation, reward
  evaluation/     # Win rate evaluation utilities
  state/          # Dataclasses: GameState, PlayerState, SiteState, ChronicleState
tests/            # 164 pytest tests covering all game mechanics
scripts/          # CLI entry points (play_interactive.py, evaluate_chronicle.py)
docs/             # Training guide (training.md)
```

## Architecture

- **GameState** (`oath/state/game_state.py`): Single source of truth. Dataclass-based. Contains players, sites, decks, banks, banners, round tracking, compound action state.
- **OathEnv** (`oath/env/oath_env.py`): PettingZoo AEC-compatible environment. Supports self-play, Clockwork Prince mode, and chronicle mode.
- **Action space**: 119 discrete actions (IDs 0-118). `ActionDecoder` (`oath/env/action_decoder.py`) maps IDs to game actions. Actions 102-118 are communication signals (no-ops for gameplay).
- **Observation**: 2248-element float32 vector + 119-element int8 action mask. Player-relative encoding.
- **Card effects**: Registered via decorators in `oath/cards/effects/`. Effect types: Action, Modifier, WhenPlayed, BattlePlan, Wake, Persistent, Rest.

## Key Conventions

- Python 3.11+, NumPy, PettingZoo 1.24+, Gymnasium 0.29+
- No linter/formatter configured — follow PEP 8 and existing code style
- Type hints used throughout
- Tests use pytest with 60-second timeout per test
- Agent interface: `act(observation: dict) -> int` where observation has `"observation"` and `"action_mask"` keys
- Player indices are 0-based; action targets use relative player offsets converted with `(player_index + offset) % num_players`

## Game Constants

- Players: 2-6 (default 4)
- Sites: 8 map locations across 3 regions (Cradle, Provinces, Hinterland)
- Rounds: max 8
- Suits: Discord, Arcane, Order, Hearth, Beast, Nomad
- Roles: Chancellor, Exile, Citizen
- Warbands: Chancellor starts with 24, Exiles with 14

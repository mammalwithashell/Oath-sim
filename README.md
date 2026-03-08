# Oath-sim

A reinforcement learning environment for the board game **Oath: Chronicles of Empire and Exile**, built on [PettingZoo](https://pettingzoo.farama.org/) and [Gymnasium](https://gymnasium.farama.org/).

## Features

- **PettingZoo AEC environment** with 119 discrete actions and 2248-dimensional observations
- **Multiple AI agents**: Random, Heuristic, Clockwork Prince (official solo automa)
- **Interactive CLI mode** for human play against AI opponents
- **Chronicle mode** for multi-game campaigns with persistent state
- **Reward shaping** for RL training (site control, banner recovery, oathkeeper bonuses)
- **230-card database** with per-card effect implementations

## Installation

```bash
# Clone and install in dev mode
git clone <repo-url>
cd Oath-sim
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Quick Start

### Play an interactive game

```bash
# Play as Player 1 (Exile) against random AI
python scripts/play_interactive.py --human 1

# Play against heuristic agents
python scripts/play_interactive.py --human 1 --agent 2 heuristic --agent 3 heuristic

# Play against Clockwork Prince (solo automa as Chancellor)
python scripts/play_interactive.py --human 1 --clockwork-prince
```

### Use as an RL environment

```python
from oath.env import OathEnv
from oath.agents import RandomAgent

env = OathEnv(num_players=4, seed=42)
agents = {i: RandomAgent(seed=i) for i in range(4)}

env.reset()
for agent_name in env.agent_iter():
    obs, reward, terminated, truncated, info = env.last()
    if terminated or truncated:
        env.step(None)
        continue
    player_idx = int(agent_name.split("_")[1])
    action = agents[player_idx].act(obs)
    env.step(action)
```

### Evaluate win rates

```bash
python scripts/evaluate_chronicle.py --num-games 100 --seed 42
```

## Project Structure

```
oath/
  agents/         # RandomAgent, HeuristicAgent, ClockworkPrinceAgent, HumanAgent
  cards/          # Card database (230 cards) and effect implementations
    effects/      # Per-card effect modules
  display/        # CLI board state renderer
  engine/         # Core game logic: actions, campaigns, win conditions
  env/            # PettingZoo AEC environment, action decoder, observations, rewards
  evaluation/     # Win rate evaluation utilities
  state/          # Dataclasses: GameState, PlayerState, SiteState, ChronicleState
tests/            # pytest test suite (164 tests)
scripts/          # CLI entry points
docs/             # Training guide
```

## Environment Details

| Property | Value |
|----------|-------|
| Action space | `Discrete(119)` |
| Observation | 2248-element `float32` vector + 119-element `int8` action mask |
| Players | 2–6 (default 4) |
| Max rounds | 8 |
| Roles | Chancellor, Exile, Citizen |

See [`docs/training.md`](docs/training.md) for detailed RL training guidance.

## Running Tests

```bash
pytest              # all tests
pytest -v           # verbose
pytest tests/test_actions.py::TestTravel  # specific test class
```

## License

See LICENSE file for details.

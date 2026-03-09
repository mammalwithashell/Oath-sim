# CLAUDE.md

## Project Overview

Oath-sim is a reinforcement learning environment for the board game **Oath: Chronicles of Empire and Exile**. It provides a PettingZoo-compatible multi-agent environment with 123 discrete actions, observation encoding, reward shaping, and several AI agents.

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
tests/            # 183 pytest tests covering all game mechanics
scripts/          # CLI entry points, training, evaluation, diagnostics
docs/             # Rule summaries, training guide (training.md)
```

## Architecture

- **GameState** (`oath/state/game_state.py`): Single source of truth. Dataclass-based. Contains players, sites, decks, banks, banners, round tracking, compound action state.
- **OathEnv** (`oath/env/oath_env.py`): PettingZoo AEC-compatible environment. Supports self-play, Clockwork Prince mode, and chronicle mode.
- **Action space**: 123 discrete actions (IDs 0-122). `ActionDecoder` (`oath/env/action_decoder.py`) maps IDs to game actions. Actions 102-118 are communication signals (no-ops). Actions 119-122 are VOW actions (oath selection after winning).
- **Observation**: 2248-element float32 vector + 123-element int8 action mask. Player-relative encoding. Oath goal is one-hot encoded (4 elements) in the global section.
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

## Training

The RL agent is trained with MaskablePPO (sb3-contrib) using `scripts/train_agent.py`.

```bash
# Basic training against heuristic opponents
python scripts/train_agent.py

# Curriculum learning with self-play
python scripts/train_agent.py --curriculum --self-play --timesteps 2000000

# Resume from checkpoint
python scripts/train_agent.py --resume models/oath_exile_latest.zip

# Diagnose a trained model (replay games with action logging)
python scripts/diagnose_agent.py models/oath_exile_latest.zip --num-games 10 --verbose
```

### Training Architecture

- **Single-agent wrapper** (`OathSingleAgentWrapper`): wraps the multi-agent env so one exile (player 1) is RL-controlled, others use fill agents (random/heuristic/self-play), Chancellor is Clockwork Prince automa
- **Oath randomization**: each episode uses a random oath goal (SUPREMACY, PEOPLE, DEVOTION, SANCTUARY) unless the agent won and vowed a specific oath
- **Vow phase**: when the agent wins, it gets one extra step to choose the next game's oath (actions 119-122). The vowed oath carries to the next episode
- **Empire knockdown**: after N consecutive wins (starts at 3), the agent's oath streak is broken with a random oath. Threshold increases by 2 each knockdown (3→5→7→...) to add variance and prevent exploiting a single oath
- **Curriculum**: random opponents → heuristic → self-play (snapshot pool)

### Key Training Mechanics

| Mechanic | Description |
|----------|-------------|
| **Oathkeeper title** | Goal-based recalculation via `recalculate_oathkeeper()` in `campaign.py`. Title only transfers when the oath goal condition changes (e.g., most sites for Supremacy). |
| **Usurper flip** | Title flips to USURPER side during Wake phase (§4.1.3), not during campaign. Exile must survive a full round after taking the title. |
| **Vow phase** | Winner picks next oath (4 VOW actions). Vision winners are locked to matching oath. Reward (+1.0) deferred to VOW step. |
| **Empire knockdown** | Consecutive win streak → random oath reset. Threshold escalates by 2 each time. |

## Rules Reference

Official rulebook PDFs are in `docs/pdfs/` (gitignored, download links below).
Concise rule summaries for QA and evaluation are in `docs/`:

- `docs/rules-core.md` — Setup, turn structure, actions, resources
- `docs/rules-combat-cards.md` — Campaigns, cards, banners, relics
- `docs/rules-victory-roles.md` — Win conditions, roles, chronicle

### PDF Sources (download to docs/pdfs/)
- Rulebook: https://cdn.1j1ju.com/medias/52/ba/4a-oath-chronicles-of-empire-exile-rulebook.pdf
- Law of Oath: https://tesera.ru/images/items/1811204/Oath_Law_of_Oath.pdf

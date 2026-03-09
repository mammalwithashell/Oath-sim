# Training RL Agents in the Oath Simulator

This guide covers how to train reinforcement learning agents using the Oath simulator environment, with a focus on the Clockwork Prince as a heuristic Chancellor opponent.

## Quick Start

```python
from oath.env.oath_env import OathEnv
from oath.agents.heuristic_agent import HeuristicAgent

# Create env with Clockwork Prince as Chancellor
env = OathEnv(num_players=4, clockwork_prince=True, seed=42)
env.reset()

# Your RL agent plays as an Exile (players 1-3)
# The Chancellor (player 0) is auto-played by the Clockwork Prince
for agent_name in env.agent_iter():
    obs, reward, terminated, truncated, info = env.last()
    if terminated or truncated:
        env.step(None)
        continue
    action = your_agent.act(obs)
    env.step(action)
```

## Environment Modes

### Self-play mode (default)

```python
env = OathEnv(num_players=4, clockwork_prince=False)
```

All 4 players are controlled externally via `env.step()`. Use this for multi-agent RL or self-play training where all players learn simultaneously.

### Clockwork Prince mode

```python
env = OathEnv(num_players=4, clockwork_prince=True)
```

Player 0 (Chancellor) is auto-played by the Clockwork Prince automa. Exile agents (players 1-3) are controlled externally. The Prince's turn is fully resolved before control passes to exile agents, so exiles only observe the post-Chancellor state.

Use this mode when training exile agents against a strong, deterministic opponent that follows the official Oath solo-play rules.

## Observation Space

Each agent receives a dictionary observation:

- **`observation`**: A 2248-element `float32` vector with player-relative encoding. Includes:
  - Current player's resources (supply, favor, secrets, warbands)
  - All site states (cards, resources, ruling player, warbands)
  - Other players' visible state (role, site, relative resource levels)
  - Banner states (People's Favor, Darkest Secret holders and values)
  - Phase and round information
  - See `oath/env/observation.py` for the full encoding.

- **`action_mask`**: A 119-element binary `int8` array. `1` = legal action, `0` = illegal.

## Action Space

119 discrete actions (IDs 0-118), grouped by type:

| Range | Action Type | Description |
|-------|------------|-------------|
| 0-7 | Travel | Move pawn to site index |
| 8-9 | Search | Draw cards from deck (8) or discard (9) |
| 10-12 | Muster | Place warbands on card slot 0-2 |
| 13-15 | Trade Favor | Gain favor from card slot 0-2 |
| 16-18 | Trade Secrets | Gain secrets from card slot 0-2 |
| 19-21 | Recover Relic | Recover relic from slot 0-2 |
| 22 | Recover PF | Recover People's Favor |
| 23 | Recover DS | Recover Darkest Secret |
| 24-28 | Campaign | Declare campaign against relative player 1-5 |
| 29-31 | Flip Adviser | Flip adviser card slot 0-2 |
| 32-34 | Use Action | Use card action slot 0-2 |
| 35-39 | Offer Citizenship | Offer to relative player 1-5 |
| 40-42 | Minor Actions | Warband placement, peek relic, add target |
| 43 | End Act Phase | Voluntarily end your turn |
| 44-48 | Communication | Signal/target (reserved) |
| 49 | Accept Citizenship | Accept citizenship offer |
| 50 | Decline Citizenship | Decline citizenship offer |
| 51 | Self-Exile | Exile yourself from Citizenship |
| 52-55 | Reliquary | Choose reliquary slot 0-3 |
| 56-58 | Battle Plan | Use battle plan from adviser slot 0-2 |
| 59 | No Battle Plan | Skip battle plan |
| 60-65 | Sacrifice | Sacrifice 0-5 warbands in campaign |
| 66-80 | Search Play | Play drawn card (3 cards x 5 destinations) |
| 81-85 | Search Discard | Discard drawn card index 0-4 |
| 86 | Campaign Target Pawn | Target pawn in campaign |
| 87 | Campaign Done | Finish selecting campaign targets |
| 88-95 | Campaign Target Site | Target site 0-7 in campaign |
| 96-100 | Campaign Target Relic | Target relic slot 0-4 |
| 101-118 | Extended | Additional compound state actions |

**Compound states** restrict available actions via the mask. During a search, only search play/discard actions are legal. During a campaign, only targeting/battle/sacrifice actions are legal.

See `oath/env/action_decoder.py` for the complete mapping.

## Reward Structure

### Terminal rewards
- **+1.0** for the game winner
- **-1.0** for all losers

### Shaped rewards (scaled by 0.01)
- Gaining the Oathkeeper title: **+3.0**
- Ruling a new site: **+1.0**
- Recovering a relic: **+0.5**
- Recovering People's Favor or Darkest Secret: **+2.0**
- Losing sites, relics, or titles: equivalent negative values

See `oath/env/reward.py` for the full reward function.

## Available Agents

### RandomAgent
Uniform random baseline. Picks any legal action with equal probability.

```python
from oath.agents.random_agent import RandomAgent
agent = RandomAgent(seed=42)
```

### HeuristicAgent
Simple priority-based agent: search > muster > trade > recover > travel > campaign > end turn.

```python
from oath.agents.heuristic_agent import HeuristicAgent
agent = HeuristicAgent(seed=42)
```

### ClockworkPrinceAgent
Official Oath solo-play automa implementing the Clockwork Prince flowchart. Chancellor-only (player 0). Features:
- **Threat assessment**: Detects successor goals, oathkeeper threats, and vision completion
- **Mind flowchart**: Four decision quadrants based on threat type
- **Ready to Fight**: Calculates whether to campaign based on warbands vs defense + caution
- **Relationship tracking**: Friends and Conspirators determine action count and card play preferences
- **Limited Powers**: Uses free card powers only (battle plans, modifiers)

```python
from oath.agents.clockwork_prince import ClockworkPrinceAgent
prince = ClockworkPrinceAgent(seed=42)
```

Typically used via the environment's `clockwork_prince=True` parameter rather than directly.

## Training Tips

1. **Start with Clockwork Prince mode** for exile agent training. The Prince provides a realistic, adaptive Chancellor opponent that follows official game design.

2. **Use `first_game=True`** (default) for a simpler card pool. The first-game setup uses 19 fixed denizens instead of the full 200+ card pool, reducing variance.

3. **The Prince adapts its strategy** based on who is winning. If your agent takes the lead (e.g., holds Oathkeeper), the Prince will shift its Mind quadrant to counter that specific threat.

4. **Key skills for exile agents to learn**:
   - When to campaign (to steal the Oathkeeper title or disrupt the Chancellor)
   - Vision pursuit (searching for and completing secret victory conditions)
   - Resource management (balancing supply, favor, and secrets)
   - Site control (ruling sites for successor goals)

5. **Curriculum learning**: Start training against `RandomAgent` opponents to learn basic mechanics, then switch to `HeuristicAgent`, then graduate to Clockwork Prince mode.

6. **Observation normalization**: The observation vector is pre-normalized to [-1, 1] range, so no additional normalization is needed.

7. **Action masking**: Always use the `action_mask` from observations. Invalid actions will cause errors. Most RL frameworks support masked action spaces.

## Example: PPO Training with Stable-Baselines3

```python
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from gymnasium import spaces, Env

from oath.env.oath_env import OathEnv
from oath.agents.heuristic_agent import HeuristicAgent


class OathSingleAgentWrapper(Env):
    """Wraps Oath's multi-agent env for single-agent training.

    Controls one exile player; other exiles use a heuristic agent.
    Chancellor is played by the Clockwork Prince.
    """

    def __init__(self, player_id=1, seed=None):
        super().__init__()
        self.player_id = player_id
        self.player_name = f"player_{player_id}"
        self._env = OathEnv(num_players=4, clockwork_prince=True, seed=seed)
        self._heuristic = HeuristicAgent(seed=seed)

        obs_space = self._env.observation_space(self.player_name)
        self.observation_space = spaces.Dict({
            "observation": obs_space["observation"],
            "action_mask": obs_space["action_mask"],
        })
        self.action_space = self._env.action_space(self.player_name)

    def reset(self, seed=None, options=None):
        self._env.reset(seed=seed)
        self._advance_to_player()
        obs = self._env.observe(self.player_name)
        return obs, {}

    def step(self, action):
        self._env.step(action)
        self._advance_to_player()
        obs, reward, term, trunc, info = self._env.last()
        # Get this player's reward
        reward = self._env._cumulative_rewards.get(self.player_name, 0.0)
        term = self._env.terminations.get(self.player_name, False)
        trunc = self._env.truncations.get(self.player_name, False)
        obs = self._env.observe(self.player_name)
        return obs, reward, term, trunc, info

    def _advance_to_player(self):
        """Step other agents until it's our turn or game is over."""
        for _ in range(1000):  # safety limit
            if not self._env.agents:
                break
            if self._env.agent_selection == self.player_name:
                break
            obs, _, term, trunc, _ = self._env.last()
            if term or trunc:
                self._env.step(None)
            else:
                action = self._heuristic.act(obs)
                self._env.step(action)


# Training
env = DummyVecEnv([lambda: OathSingleAgentWrapper(player_id=1, seed=42)])
model = PPO("MultiInputPolicy", env, verbose=1, n_steps=2048, batch_size=64)
model.learn(total_timesteps=1_000_000)
model.save("oath_exile_ppo")
```

> **Note**: The wrapper above is a starting point. For production training, use
> `scripts/train_agent.py` which includes action masking, curriculum learning,
> self-play, and diagnostic checkpoints.

---

## 4-Stage Curriculum Pipeline

The recommended training methodology uses a 4-stage curriculum that progressively increases difficulty. Each stage builds on skills learned in the previous one.

### Stage Overview

| Stage | Fill Agent (Exiles 2-3) | Chancellor (Player 0) | What the Agent Learns |
|-------|------------------------|-----------------------|----------------------|
| 0: random | RandomAgent | RandomAgent | Legal actions, basic game mechanics, resource collection |
| 1: heuristic | HeuristicAgent | HeuristicAgent | Beat priority-based opponents, campaign timing |
| 2: clockwork-prince | HeuristicAgent | Clockwork Prince automa | Beat the adaptive official AI, handle threat response |
| 3: self-play | Frozen snapshots | Clockwork Prince automa | Counter-strategies, robust play against trained agents |

### How Stages Work

- **Stages 0-1** run with `clockwork_prince=False`. The Chancellor is just another fill agent (random or heuristic), making these stages easier. The agent can focus on learning mechanics without facing the full automa.

- **Stage 2** enables the Clockwork Prince automa (`clockwork_prince=True`). This is a significant difficulty jump — the Prince adapts its strategy, targets threats, and campaigns intelligently. Other exiles remain heuristic.

- **Stage 3** keeps the Clockwork Prince and swaps exile opponents with frozen snapshots of the agent itself. A snapshot pool (default 5 recent models) provides diversity. The agent learns to beat earlier versions of itself.

### Promotion

The agent advances to the next stage when its rolling win rate exceeds a threshold:

- **Default threshold**: 35% win rate (`--promote-threshold 0.35`)
- **Rolling window**: Last 200 games (`--promote-window 200`)
- **Check frequency**: Every 50 completed games
- Win tracking resets on promotion for clean stage evaluation

### Run Commands

```bash
# Full curriculum with self-play (recommended)
python scripts/train_agent.py --curriculum --self-play --timesteps 2000000 --seed 42

# Curriculum without self-play (stops after clockwork-prince stage)
python scripts/train_agent.py --curriculum --timesteps 1000000

# Skip curriculum, train directly against heuristic with Clockwork Prince
python scripts/train_agent.py --opponent heuristic --timesteps 500000
```

### Expected Training Progression

| Stage | Typical Duration | Signs of Progress |
|-------|-----------------|-------------------|
| random | 50K-100K steps | Win rate climbs from ~25% to 35%+ |
| heuristic | 200K-400K steps | Learns to campaign, use search, manage resources |
| clockwork-prince | 300K-500K steps | Adapts to Prince's threat-response behavior |
| self-play | Remainder | Win rate stabilizes, diverse strategies emerge |

---

## Smoke Test

Before any full training run, validate the pipeline end-to-end:

```bash
python scripts/train_agent.py --smoke-test
```

This runs 20K timesteps through all 4 stages with lowered promotion thresholds (15% win rate, 20-game window). It automatically enables curriculum and self-play.

### What It Validates

- Environment creation with and without Clockwork Prince
- Curriculum promotion between all 4 stages
- Self-play snapshot saving and loading
- Diagnostic QA checkpoints at each stage transition
- Model saving and loading

### Expected Behavior

- Runtime: ~2-5 minutes
- May not reach all stages in 20K steps (depends on game length)
- **Pass criteria**: No crashes, model saves successfully, at least one QA checkpoint runs
- Promotions happen quickly due to lowered thresholds — this is intentional for validation

---

## QA Checkpoints

Diagnostic QA runs automatically between curriculum stages and after training completes. Each checkpoint:

1. **Saves the model** to `models/stage_{name}.zip`
2. **Plays 20 games** with deterministic policy against heuristic opponents
3. **Checks for degenerate behavior**:
   - Single action used >80% of the time
   - Fewer than 5 distinct actions (strategy collapse)
   - 0% win rate (agent not learning)
4. **Prints a QA report** with win rate, win types, action diversity, and warnings

### Example QA Output

```
  [QA] Stage 'heuristic' checkpoint (20 games):
    Win rate: 40.0%
    Win types: {'OATHKEEPER': 4, 'TIMEOUT': 12, 'VISION': 4}
    Distinct actions: 23
    Top actions: #43(85x), #8(42x), #10(31x)
    No degenerate behavior detected
    Checkpoint saved: models/stage_heuristic.zip
```

### Warning Signs

| Warning | What It Means | Action |
|---------|---------------|--------|
| Single action >80% | Agent found a degenerate loop | Increase entropy coefficient, lower learning rate |
| <5 distinct actions | Strategy collapse | Reset to earlier checkpoint, increase exploration |
| 0% win rate after promotion | Stage too hard too fast | Lower promote-threshold, increase promote-window |
| All wins via TIMEOUT | Agent stalls without pursuing victory | Check reward shaping, ensure shaped rewards are reaching agent |

### Manual Diagnostics

Run detailed diagnostics on any checkpoint:

```bash
# Full action trace with Clockwork Prince
python scripts/diagnose_agent.py models/stage_clockwork-prince.zip --num-games 20

# Without Clockwork Prince (for stages 0-1)
python scripts/diagnose_agent.py models/stage_random.zip --no-clockwork-prince --num-games 20

# Statistical evaluation with confidence intervals
python scripts/evaluate_agent.py models/stage_final.zip --num-games 100
python scripts/evaluate_agent.py models/stage_heuristic.zip --no-clockwork-prince --num-games 50
```

---

## Tuning Promotion Thresholds

| Parameter | Default | Conservative | Aggressive |
|-----------|---------|-------------|------------|
| `--promote-threshold` | 0.35 | 0.45-0.50 | 0.20-0.25 |
| `--promote-window` | 200 | 300-500 | 50-100 |

- **Higher thresholds** = more time per stage, stronger fundamentals before advancing
- **Lower thresholds** = faster progression, risk of underfitting early stages
- The per-stage default is uniform (35% for all). For longer runs, consider restarting with higher thresholds after reviewing QA output from an initial run

---

## Full Training Run Checklist

1. **Smoke test**: `python scripts/train_agent.py --smoke-test`
2. **Review smoke test output**: Check for crashes, verify QA checkpoints ran
3. **Start full run**:
   ```bash
   python scripts/train_agent.py --curriculum --self-play --timesteps 2000000 --seed 42
   ```
4. **Monitor**: Watch TensorBoard (`tensorboard --logdir logs/`) for win rate curves
5. **Review QA checkpoints**: Check console output between stage promotions
6. **Post-training QA**:
   ```bash
   python scripts/diagnose_agent.py models/oath_exile_latest.zip --num-games 20 --verbose
   python scripts/evaluate_agent.py models/oath_exile_latest.zip --num-games 100
   ```
7. **Validate win conditions**: Verify win types are diverse (not all TIMEOUT), action usage is varied, and the agent uses meaningful strategies (campaigns, searches, site control)

# Plan: Oath-sim Web Frontend — Interactive Play Mode

## Goal
Build a web app where a human can play Oath against AI agents (random, heuristic, or any combination) through a browser UI.

## Stack
- **Frontend**: React 18 + TypeScript + Tailwind CSS (via Vite)
- **Backend**: FastAPI serving the existing `OathEnv` game engine
- **Communication**: REST — human submits actions, backend runs AI turns and returns updated state

## How It Works

1. Human opens the app → **Setup screen**: pick number of players (2-6), assign each seat to human or an AI type (random / heuristic / clockwork prince)
2. Click "Start Game" → backend creates an `OathEnv`, AI agents auto-play until it's the human's turn
3. **Game screen** shows the full board. Human picks from legal actions. Backend applies the action, runs all AI turns, returns new state
4. Repeat until game over → show winner

## Backend: `oath/api/` (4 files)

### `oath/api/app.py`
FastAPI app with CORS middleware. Mounts routes. Single entry point: `uvicorn oath.api.app:app`.

### `oath/api/game_manager.py`
Manages game sessions in memory.

```python
class GameSession:
    game_id: str
    env: OathEnv
    agents: dict[int, RandomAgent | HeuristicAgent]
    human_players: set[int]
    action_log: list[dict]           # all actions taken (for game log)
    pending_ai_actions: list[dict]   # AI actions taken since last human query

    def advance_until_human(self):
        """Loop: get current player, if AI → act + step, log it. Stop when human's turn or game over."""

    def apply_human_action(self, action_id: int):
        """Step with action_id, then advance_until_human()."""

class GameManager:
    sessions: dict[str, GameSession]
    def create(config) -> GameSession
    def get(game_id) -> GameSession
    def delete(game_id)
```

### `oath/api/serializers.py`
Converts `GameState` → JSON dict. Resolves card IDs to `{id, name, suit}` via `get_card()`. Hides opponent facedown advisers. Uses existing `describe_action()` from `oath/display/renderer.py` for action descriptions.

Key functions:
- `serialize_state(gs, viewer_index) → dict` — full board for frontend
- `serialize_actions(gs, player_index, action_mask) → list[dict]` — legal actions with descriptions + action_type grouping
- `serialize_compound(gs) → dict | None` — search/campaign/citizenship context

### `oath/api/routes.py`
Three endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/games` | Create game → returns `{game_id, state}` |
| `GET` | `/api/games/{id}/state` | Get current state + legal actions |
| `POST` | `/api/games/{id}/action` | Submit human action → returns updated state |

Every response returns the same shape:
```json
{
  "game_id": "abc123",
  "game_state": {
    "round_number": 3,
    "phase": "ACT",
    "oath_goal": "SUPREMACY",
    "successor_goal": "MOST_SITES",
    "current_player_index": 1,
    "is_game_over": false,
    "winner": null,
    "win_type": null,
    "oathkeeper_holder": 0,
    "oathkeeper_side": "OATHKEEPER",
    "peoples_favor": { "holder": null, "tokens": 1 },
    "darkest_secret": { "holder": 0, "tokens": 2 },
    "favor_banks": { "Discord": 3, "Arcane": 2, ... },
    "shared_secrets": 8,
    "world_deck_size": 5,
    "relic_deck_size": 3,
    "sites": [
      {
        "index": 0, "name": "Plains", "region": "CRADLE",
        "defense": 1, "is_faceup": true,
        "ruling_player": 0, "warbands": 3,
        "cards": [
          { "slot": 0, "id": 1, "name": "Keep", "suit": "Order", "favor": 0, "secrets": 0 },
          { "slot": 1, "id": 5, "name": "The Old Oak", "suit": "Beast", "favor": 0, "secrets": 0 },
          null
        ],
        "relics": [{ "id": 211, "name": "Ivory Eye" }],
        "pawns": [0, 2]
      }, ...
    ],
    "players": [
      {
        "index": 0, "role": "CHANCELLOR", "pawn_site": 0,
        "supply": 7, "favor": 2, "secrets": 1,
        "warbands_bank": 21, "warbands_board": 3,
        "advisers": [
          { "slot": 0, "id": 3, "name": "Errand Boy", "suit": "Beast", "faceup": false }
        ],
        "relics": [],
        "vision": null
      }, ...
    ],
    "compound_state": null
  },
  "is_human_turn": true,
  "human_player_index": 1,
  "legal_actions": [
    { "action_id": 0, "action_type": "TRAVEL", "description": "Travel to Plains [site 0, Cradle]" },
    { "action_id": 8, "action_type": "SEARCH", "description": "Search the deck" },
    { "action_id": 10, "action_type": "MUSTER", "description": "Muster: Keep (Order) [slot 0]" },
    ...
  ],
  "ai_actions": [
    { "player": 0, "role": "CHANCELLOR", "description": "Muster: Keep (Order) [slot 0]" },
    { "player": 0, "role": "CHANCELLOR", "description": "End act phase" }
  ],
  "action_log": [ ... ]
}
```

## Frontend: `frontend/` (Vite + React + TS + Tailwind)

### File Structure
```
frontend/
  src/
    api/client.ts              # fetch wrappers for 3 endpoints
    types/game.ts              # TS interfaces matching API response
    hooks/useGame.ts           # state management: create, poll, act
    components/
      GameSetup.tsx            # lobby screen
      GameBoard.tsx            # main layout
      BannerBar.tsx            # top bar: oath, round, banners, favor banks
      MapView.tsx              # 3 regions with site cards
      SiteCard.tsx             # single site: cards, relics, pawns, ruler
      PlayerPanel.tsx          # player info: role, resources, advisers
      ActionPanel.tsx          # clickable legal actions grouped by type
      CompoundPanel.tsx        # search/campaign/citizenship sub-actions
      GameLog.tsx              # scrollable action history
      GameOverModal.tsx        # winner announcement
    App.tsx                    # routes between Setup and Board
    main.tsx                   # entry point
```

### GameSetup.tsx
- Dropdown: number of players (2-6)
- For each player slot: radio buttons — "Human" / "Random" / "Heuristic"
- Optional seed input
- "Start Game" button → `POST /api/games` → navigate to GameBoard

### GameBoard.tsx — Layout
```
┌─────────────────────────────────────────────────┐
│  BannerBar                                      │
│  Round 3/8 | SUPREMACY | PF: P2 | DS: unclaimed │
├───────────────────────┬─────────────────────────┤
│                       │  PlayerPanel (P0) ★     │
│  MapView              │  PlayerPanel (P1) ← YOU │
│  ┌─[CRADLE]─────┐    │  PlayerPanel (P2)        │
│  │ Site 0  Site 1│    │  PlayerPanel (P3)        │
│  ├─[PROVINCES]───┤    │                         │
│  │ Site 2  Site 3│    ├─────────────────────────┤
│  │ Site 4        │    │  ActionPanel            │
│  ├─[HINTERLAND]──┤    │  [Travel ▾] [Search ▾] │
│  │ Site 5  Site 6│    │  [Muster ▾] [Trade ▾]  │
│  │ Site 7        │    │  [Campaign] [End Turn]  │
│  └───────────────┘    │                         │
├───────────────────────┴─────────────────────────┤
│  GameLog                                        │
│  P0 (Chancellor): Muster: Keep (Order)          │
│  P0 (Chancellor): End act phase                 │
│  > Your turn                                    │
└─────────────────────────────────────────────────┘
```

### SiteCard.tsx
- Header: site name + defense shield icon + region color bar
- Card slots: up to 3 rows showing card name, suit color dot, favor/secret tokens
- Relic list (small badges)
- Pawn dots (colored circles for each player present)
- Ruler banner + warband count
- Facedown: gray card back with "?" — no card/relic info

### PlayerPanel.tsx
- Role badge with color (Chancellor=amber, Exile=slate, Citizen=sky)
- Resource row: supply / favor / secrets / warbands (bank+board)
- Adviser slots (up to 3): card name + suit dot + faceup/facedown icon
- Highlight ring when active turn
- "(You)" label on the human's panel

### ActionPanel.tsx
- Only shown when `is_human_turn === true`
- Actions grouped by `action_type` into collapsible sections
- Each action is a button with the description text
- Click → `POST /api/games/{id}/action` with `action_id`
- During compound states, shows CompoundPanel instead

### CompoundPanel.tsx
- **Search**: drawn card list with "Play to site" / "Play as adviser" / "Discard" buttons per card
- **Campaign targets**: target checkboxes (sites/relics/pawn) + "Done" button
- **Campaign battle plan**: adviser card buttons + "Skip" button
- **Campaign sacrifice**: numbered buttons (0-5 warbands)
- **Citizenship**: "Accept" / "Decline" buttons

### GameLog.tsx
- Scrollable list, auto-scrolls to bottom
- Each entry: `[P0 Chancellor] Muster: Keep (Order) [slot 0]`
- Color-coded by player
- Human actions distinguished with bold/"You" prefix

### Tailwind Theme
- **Suit colors**: Discord=`purple-500`, Arcane=`blue-500`, Order=`yellow-500`, Hearth=`red-500`, Beast=`green-500`, Nomad=`orange-500`
- **Role colors**: Chancellor=`amber-400`, Exile=`slate-400`, Citizen=`sky-400`
- Dark background (`slate-900`), card surfaces (`slate-800`), text (`slate-100`)
- Desktop-first responsive layout

## Implementation Order

### Step 1: Backend API
1. `oath/api/__init__.py`
2. `oath/api/serializers.py` — serialize GameState, actions, compound state
3. `oath/api/game_manager.py` — session create/get/delete + AI auto-advance loop
4. `oath/api/routes.py` — 3 endpoints
5. `oath/api/app.py` — FastAPI app with CORS

### Step 2: Frontend scaffold
6. Init Vite project with React + TS + Tailwind
7. `src/types/game.ts` — TypeScript interfaces
8. `src/api/client.ts` — API fetch functions
9. `src/hooks/useGame.ts` — game state hook
10. `src/App.tsx` — setup vs board routing

### Step 3: Core components
11. `GameSetup.tsx` — lobby
12. `BannerBar.tsx` — header info
13. `SiteCard.tsx` — site display
14. `MapView.tsx` — region layout with sites
15. `PlayerPanel.tsx` — player info
16. `ActionPanel.tsx` — action buttons
17. `GameBoard.tsx` — main layout composing all above

### Step 4: Compound actions + finishing
18. `CompoundPanel.tsx` — search/campaign/citizenship modals
19. `GameLog.tsx` — action history
20. `GameOverModal.tsx` — winner screen

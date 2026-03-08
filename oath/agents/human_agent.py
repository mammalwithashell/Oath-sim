"""Human agent that prompts for input via CLI."""

from __future__ import annotations

from typing import Optional

from oath.state.game_state import GameState
from oath.display.renderer import render_full_board, render_compound_context, render_action_menu


class HumanAgent:
    """Interactive agent that displays game state and prompts for actions.

    Before calling act(), the game loop must call set_game_state() to provide
    the raw GameState for rich display rendering.
    """

    def __init__(self, player_index: int, seed: Optional[int] = None):
        self.player_index = player_index
        self._game_state: Optional[GameState] = None

    def set_game_state(self, gs: GameState) -> None:
        """Provide current game state for display. Called before act()."""
        self._game_state = gs

    def act(self, observation: dict) -> int:
        """Display board state, show legal actions, and prompt for choice."""
        gs = self._game_state
        mask = observation["action_mask"]

        if gs is not None:
            print(render_full_board(gs, self.player_index))

            if gs.in_compound_action:
                print(render_compound_context(gs))

        menu_text, menu_map = render_action_menu(gs, self.player_index, mask)
        print(menu_text)

        if not menu_map:
            print("No legal actions available.")
            return 43  # END_ACT_PHASE fallback

        while True:
            try:
                raw = input("Enter choice: ").strip()
                choice = int(raw)
                if choice in menu_map:
                    return menu_map[choice]
                print(f"Invalid choice. Pick 1-{len(menu_map)}.")
            except ValueError:
                print("Enter a number.")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                raise SystemExit(0)

    def reset(self) -> None:
        """Reset internal state for a new game."""
        self._game_state = None

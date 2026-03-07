"""Post-game chronicle system (deck mutation).

Handles the legacy aspect of Oath where the world deck changes
between games based on game outcomes.
"""

from __future__ import annotations

from oath.state.game_state import GameState


def apply_chronicle(gs: GameState) -> dict:
    """Apply post-game chronicle effects.

    Returns a dict describing the changes for the next game setup.
    This is a stub — full implementation would track:
    - Which cards to add/remove from the world deck
    - Which sites to keep/replace
    - Oath goal changes based on winner
    """
    result = {
        "winner": gs.winner,
        "oath_goal": gs.oath_goal,
        "cards_in_play": [],
        "cards_removed": [],
    }

    # In a full implementation, cards at sites controlled by the winner
    # would be more likely to appear in the next game's deck
    return result

"""Scryer (OATH-019) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 12: Scryer (OATH-019) ─────────────────────────────────────
# Action: Peek at any one discard pile.
# In the RL simulator, this is largely a no-op since info is encoded
# in observations. We implement it as a free action that reveals
# discard pile info (no state change needed for RL purposes).
def _scryer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # In a full implementation, this would reveal hidden information.
    # For the RL simulator, discard piles are already observable.
    return gs

register_effect(12, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_scryer_execute,
    description="Action: Peek at any discard pile",
))

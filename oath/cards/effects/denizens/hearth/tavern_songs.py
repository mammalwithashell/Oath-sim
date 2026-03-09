"""Tavern Songs (OATH-054) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 55: Tavern Songs ──────────────────────────────────────────
# Action: Peek at discard pile (no-op for RL).
def _tavern_songs_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # No-op for RL: discard piles are already observable.
    return gs

register_effect(55, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_tavern_songs_execute,
    description="Action: Peek at discard pile (no-op for RL)",
))

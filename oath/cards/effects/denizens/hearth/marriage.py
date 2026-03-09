"""Marriage (OATH-148) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 149: Marriage ─────────────────────────────────────────────
# Persistent: Counts as 2 Hearth advisers (simplified: no-op).
def _marriage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op. Counting logic handled elsewhere.
    return gs

register_effect(149, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_marriage_execute,
    description="Persistent: Counts as 2 Hearth advisers (no-op)",
))

"""Council Seat (OATH-123) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 124: Council Seat ──────────────────────────────────────────
# Persistent: If Citizen, cannot be exiled (simplified: no-op)
def _council_seat_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(124, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_council_seat_execute,
    description="Persistent: If Citizen, cannot be exiled (no-op)",
))

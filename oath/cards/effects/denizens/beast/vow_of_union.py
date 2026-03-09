"""Vow of Union (OATH-185) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 186: Vow of Union ─────────────────────────────────────────
# Persistent: Warbands at ruled sites add to attacking force.
# Simplified: no-op.
def _vow_of_union_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(186, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_union_execute,
    description="Persistent: Warbands at ruled sites add to attack (no-op)",
))

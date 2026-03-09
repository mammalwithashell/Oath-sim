"""Vow of Renewal (OATH-086) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 87: Vow of Renewal ───────────────────────────────────────
# Persistent: Can't recover People's Favor.
# Simplified: no-op.
def _vow_of_renewal_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(87, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_renewal_execute,
    description="Persistent: Can't recover People's Favor (no-op)",
))

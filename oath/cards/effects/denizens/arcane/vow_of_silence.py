"""Vow of Silence (OATH-074) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 75: Vow of Silence ────────────────────────────────────────
# Modifier(Recover): Can't recover Darkest Secret.
# Simplified: no-op.
def _vow_of_silence_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(75, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_vow_of_silence_execute,
    description="Recover: Can't recover Darkest Secret (no-op in simulator)",
))

"""Initiation Rite (OATH-073) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 74: Initiation Rite ───────────────────────────────────────
# Modifier(Muster): Must place secrets instead of favor to muster.
# Simplified: set _modifier_bool.
def _initiation_rite_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(74, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_initiation_rite_execute,
    description="Muster: Must place secrets instead of favor",
))

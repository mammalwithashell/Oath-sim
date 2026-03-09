"""Rowdy Pub (OATH-144) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 145: Rowdy Pub ────────────────────────────────────────────
# Modifier(Muster): Gain 1 more warband when mustering from this card.
def _rowdy_pub_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(145, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_rowdy_pub_execute,
    description="Muster: Gain 1 more warband when mustering from this card",
))

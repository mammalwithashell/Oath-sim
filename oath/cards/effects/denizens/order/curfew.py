"""Curfew (OATH-119) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 120: Curfew ────────────────────────────────────────────────
# Modifier(Trade): Enemies must pay favor to trade at ruled sites (simplified: no-op)
def _curfew_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(120, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_curfew_execute,
    description="Modifier(Trade): Enemies pay favor to trade at ruled sites (no-op)",
))

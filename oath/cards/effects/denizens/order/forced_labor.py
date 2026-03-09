"""Forced Labor (OATH-112) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 113: Forced Labor ──────────────────────────────────────────
# Modifier(Search): Enemies can't search at ruled sites without paying favor
# Simplified: no-op for RL
def _forced_labor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(113, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_forced_labor_execute,
    description="Modifier(Search): Enemies pay favor to search at ruled sites (no-op)",
))

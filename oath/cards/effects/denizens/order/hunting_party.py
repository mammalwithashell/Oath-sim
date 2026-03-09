"""Hunting Party (OATH-122) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 123: Hunting Party ─────────────────────────────────────────
# Modifier(Search): After searching, gain 1 supply
def _hunting_party_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(123, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_hunting_party_execute,
    description="Modifier(Search): Gain 1 supply after searching",
))

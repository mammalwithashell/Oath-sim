"""Toll Roads (OATH-118) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 119: Toll Roads ────────────────────────────────────────────
# Modifier(Travel): Enemies must pay favor to travel to ruled sites
def _toll_roads_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(119, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_toll_roads_execute,
    description="Modifier(Travel): Enemies pay favor to travel to ruled sites",
))

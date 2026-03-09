"""Tyrant (OATH-111) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 112: Tyrant ────────────────────────────────────────────────
# Modifier(Travel): Must kill a warband at travel destination (set _modifier_bool flag)
def _tyrant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(112, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_tyrant_execute,
    description="Modifier(Travel): Must kill a warband at destination",
))

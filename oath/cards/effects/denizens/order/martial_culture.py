"""Martial Culture (OATH-010) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 22: Martial Culture ────────────────────────────────────────
# Battle Plan: If Exile defeats Exile, may become Citizen
# Simplified: gain supply refresh (gain 1 supply)
def _martial_culture_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(22, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_martial_culture_execute,
    description="Battle Plan: Gain supply refresh (simplified citizenship)",
))

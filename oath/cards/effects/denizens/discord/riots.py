"""Riots (OATH-091) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 92: Riots ────────────────────────────────────────────────
# When Played: If People's Favor on Mob side, discard common suit.
# Simplified: gain 2 warbands.
def _riots_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(92, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_riots_execute,
    description="When Played: Gain 2 warbands (simplified)",
))

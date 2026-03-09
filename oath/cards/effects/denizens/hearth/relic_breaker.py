"""Relic Breaker (OATH-139) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 140: Relic Breaker ────────────────────────────────────────
# Action: Put relic on bottom of deck, gain 3 warbands
# (simplified: gain 3 warbands).
def _relic_breaker_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(140, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_relic_breaker_execute,
    description="Action: Gain 3 warbands (break a relic)",
))

"""Threatening Roar (OATH-179) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 180: Threatening Roar ─────────────────────────────────────
# When Played: Discard all Nomad and Beast cards at sites in region.
# Simplified: gain 2 warbands.
def _threatening_roar_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(180, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_threatening_roar_execute,
    description="When Played: Gain 2 warbands (simplified discard Nomad/Beast)",
))

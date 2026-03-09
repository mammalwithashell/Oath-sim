"""False Prophet (OATH-085) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 86: False Prophet ────────────────────────────────────────
# When Played: If Exile, gain 1 warband.
# Simplified: gain 1 warband.
def _false_prophet_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 1)

register_effect(86, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_false_prophet_execute,
    description="When Played: Gain 1 warband (simplified)",
))

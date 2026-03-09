"""Key to the City (OATH-018) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 28: Key to the City ──────────────────────────────────────
# When Played: Kill warbands at site if ruler absent, gain+place warband.
# Simplified: gain 2 warbands.
def _key_to_the_city_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(28, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_key_to_the_city_execute,
    description="When Played: Gain 2 warbands (simplified)",
))

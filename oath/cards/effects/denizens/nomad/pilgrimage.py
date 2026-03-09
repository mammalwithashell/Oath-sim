"""Pilgrimage (OATH-161) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 162: Pilgrimage ───────────────────────────────────────────
# WHEN_PLAYED: Discard all denizens at site, draw same number
# (simplified: gain 2 favor)
def _pilgrimage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(162, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_pilgrimage_execute,
    description="When Played: Gain 2 favor (simplified site refresh)",
))

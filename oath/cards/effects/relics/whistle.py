"""Whistle (OATH-218) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 217: Relic 7 (Whistle, OATH-218) ──────────────────────────
# Action: Choose pawn at another site, they must travel to you
# Simplified: gain 1 supply
def _whistle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(217, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_whistle_execute,
    description="Action: Summon player to your site",
))

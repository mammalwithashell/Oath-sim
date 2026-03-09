"""Brass Horse (OATH-213) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 220: Relic 10 (Brass Horse, OATH-213) ────────────────────
# Action: Travel for free based on discard pile top card
# Simplified: gain 2 supply
def _brass_horse_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(220, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_brass_horse_execute,
    description="Action: Free travel based on discard",
))

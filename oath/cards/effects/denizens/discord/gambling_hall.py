"""Gambling Hall (OATH-093) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 94: Gambling Hall ────────────────────────────────────────
# Action: Roll dice, gain favor equal to shields rolled.
# Simplified: gain 2 favor.
def _gambling_hall_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(94, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_gambling_hall_execute,
    description="Action: Gain 2 favor (simplified from dice roll)",
))

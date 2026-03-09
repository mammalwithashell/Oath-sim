"""Wayside Inn (OATH-047) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 14: Wayside Inn (OATH-047) ────────────────────────────────
# Action: Gain 2 Supply.
def _wayside_inn_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(14, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wayside_inn_execute,
    description="Action: Gain 2 Supply",
))

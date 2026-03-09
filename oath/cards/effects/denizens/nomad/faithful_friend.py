"""Faithful Friend (OATH-028) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 35: Faithful Friend ───────────────────────────────────────
# WHEN_PLAYED: Gain 4 supply
def _faithful_friend_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 4)

register_effect(35, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_faithful_friend_execute,
    description="When Played: Gain 4 supply",
))

"""Elders (OATH-026) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


def _elders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Gain 1 favor from any bank (take from largest)
    best_bank = max(range(len(gs.favor_banks)), key=lambda i: gs.favor_banks[i])
    if gs.favor_banks[best_bank] > 0:
        gs.favor_banks[best_bank] -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(3, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_elders_execute,
    description="Action: Gain 1 favor",
))

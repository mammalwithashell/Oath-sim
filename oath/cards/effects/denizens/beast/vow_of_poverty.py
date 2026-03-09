"""Vow of Poverty (OATH-193) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 194: Vow of Poverty ───────────────────────────────────────
# Rest: If you have no favor, gain 2 favor from any bank.
def _vow_of_poverty_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].favor == 0

def _vow_of_poverty_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(194, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_vow_of_poverty_condition,
    execute=_vow_of_poverty_execute,
    description="Rest: If no favor, gain 2 favor from any bank",
))

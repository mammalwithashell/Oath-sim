"""Naysayers (OATH-021) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Role

if TYPE_CHECKING:
    from oath.state.game_state import GameState


def _naysayers_condition(gs: 'GameState', player_index: int) -> bool:
    # Check if any Exile holds the Oathkeeper title
    holder = gs.oathkeeper_holder
    if holder is not None and holder != gs.chancellor_index:
        if gs.players[holder].role in (Role.EXILE, Role.CITIZEN):
            return True
    return False

def _naysayers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    chancellor = gs.players[gs.chancellor_index]
    if chancellor.favor > 0:
        chancellor.favor -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(6, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_naysayers_condition,
    execute=_naysayers_execute,
    description="Rest: Take favor from Chancellor if Exile is Oathkeeper",
))

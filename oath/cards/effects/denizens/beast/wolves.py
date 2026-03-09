"""Wolves (OATH-039) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 44: Wolves ────────────────────────────────────────────────
# Action: Kill 1 warband on any board.
def _wolves_condition(gs: 'GameState', player_index: int) -> bool:
    # Check if any other player has warbands on their board
    for i, p in enumerate(gs.players):
        if i != player_index and p.warbands_board > 0:
            return True
    return False

def _wolves_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Kill 1 warband from the first opponent who has warbands
    for i, p in enumerate(gs.players):
        if i != player_index and p.warbands_board > 0:
            p.warbands_board -= 1
            break
    return gs

register_effect(44, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_wolves_condition,
    execute=_wolves_execute,
    description="Action: Kill 1 warband on any board",
))

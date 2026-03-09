"""Awaited Return (OATH-150) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 151: Awaited Return ───────────────────────────────────────
# Modifier(Trade): Spend no supply if sacrifice 1 warband.
def _awaited_return_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board > 0

def _awaited_return_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    if player.warbands_board > 0:
        player.warbands_board -= 1
        # Signal free trade
        gs._modifier_int = 0
    return gs

register_effect(151, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=_awaited_return_condition,
    execute=_awaited_return_execute,
    description="Trade: Spend no supply if sacrifice 1 warband",
))

"""A Fast Steed (OATH-172) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 173: A Fast Steed ─────────────────────────────────────────
# MODIFIER(Travel): Spend no supply if 3 or fewer warbands on board
def _a_fast_steed_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board <= 3

def _a_fast_steed_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(173, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=_a_fast_steed_condition,
    execute=_a_fast_steed_execute,
    description="Travel: Free travel if 3 or fewer warbands on board",
))

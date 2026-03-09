"""Wild Cry (OATH-189) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_supply, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 190: Wild Cry ─────────────────────────────────────────────
# Modifier(Search): If playing Beast card, gain 1 supply and 2 warbands.
def _wild_cry_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_supply(gs, player_index, 1)
    gs = gain_warbands(gs, player_index, 2)
    return gs

register_effect(190, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_wild_cry_execute,
    description="Search: If playing Beast card, gain 1 supply and 2 warbands",
))

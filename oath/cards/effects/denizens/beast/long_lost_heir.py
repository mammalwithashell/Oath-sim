"""Long-Lost Heir (OATH-044) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 46: Long-Lost Heir ────────────────────────────────────────
# When Played: If Exile, may become Citizen. Simplified: gain 3 supply.
def _long_lost_heir_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 3)

register_effect(46, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_long_lost_heir_execute,
    description="When Played: Gain 3 supply (simplified become Citizen)",
))

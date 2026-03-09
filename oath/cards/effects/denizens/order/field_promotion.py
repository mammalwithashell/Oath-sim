"""Field Promotion (OATH-106) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 107: Field Promotion ───────────────────────────────────────
# Battle Plan: If victorious, gain 3 warbands
def _field_promotion_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(107, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_field_promotion_execute,
    description="Battle Plan: If victorious, gain 3 warbands",
))

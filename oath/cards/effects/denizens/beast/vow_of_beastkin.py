"""Vow of Beastkin (OATH-196) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 197: Vow of Beastkin ──────────────────────────────────────
# Modifier(Muster): Must muster on matching adviser card, gain 1
# more warband. Simplified: gain 1 extra warband.
def _vow_of_beastkin_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_warbands(gs, player_index, 1)
    return gs

register_effect(197, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_vow_of_beastkin_execute,
    description="Muster: Gain 1 extra warband",
))

"""Relic Worship (OATH-173) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 174: Relic Worship ────────────────────────────────────────
# MODIFIER(Recover): After recovering relic, gain 3 supply
def _relic_worship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 3)

register_effect(174, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_relic_worship_execute,
    description="Recover: Gain 3 supply after recovering a relic",
))

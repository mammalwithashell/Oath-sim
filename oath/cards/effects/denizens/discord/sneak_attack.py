"""Sneak Attack (OATH-098) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 99: Sneak Attack ─────────────────────────────────────────
# Modifier(Campaign): After another player's campaign, may campaign free.
# Simplified: gain 1 supply.
def _sneak_attack_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(99, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_sneak_attack_execute,
    description="Campaign: Gain 1 supply (simplified from free campaign after enemy campaign)",
))

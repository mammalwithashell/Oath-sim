"""Gleaming Armor (OATH-066) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 67: Gleaming Armor ────────────────────────────────────────
# Modifier(Campaign): Enemy battle plans cost extra secret.
# Simplified: +1 defense die.
def _gleaming_armor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 1
    return gs

register_effect(67, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_gleaming_armor_execute,
    description="Campaign: +1 defense die (simplified from extra battle plan cost)",
))

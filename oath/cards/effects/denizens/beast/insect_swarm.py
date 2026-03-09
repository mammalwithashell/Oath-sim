"""Insect Swarm (OATH-184) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 185: Insect Swarm ─────────────────────────────────────────
# Modifier(Campaign): Enemy battle plans cost extra favor.
# Simplified: +1 defense die.
def _insect_swarm_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(185, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_insect_swarm_execute,
    description="Campaign: Enemy battle plans cost extra favor (+1 defense die)",
))

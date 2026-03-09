"""Billowing Fog (OATH-059) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 60: Billowing Fog ─────────────────────────────────────────
# Battle Plan: If defeated, kill no warbands.
# Simplified: +3 defense dice.
def _billowing_fog_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 3
    elif cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 3
    return gs

register_effect(60, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_billowing_fog_execute,
    description="Battle Plan: +3 defense dice (simplified from no kills if defeated)",
))

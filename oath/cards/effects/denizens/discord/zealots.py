"""Zealots (OATH-087) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 88: Zealots ──────────────────────────────────────────────
# Battle Plan: If defending force larger, sacrificed warbands add 3 each.
# Simplified: +3 attack dice if defending force is larger.
def _zealots_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Only apply if defending force is larger than attacking force
    if cs.campaign_defense_dice > cs.campaign_attack_dice:
        cs.campaign_attack_dice += 3
    return gs

register_effect(88, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_zealots_execute,
    description="Battle Plan: +3 attack dice (simplified from sacrifice bonus)",
))

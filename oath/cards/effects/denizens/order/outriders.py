"""Outriders (OATH-104) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 105: Outriders ─────────────────────────────────────────────
# Battle Plan: Ignore all skulls YOU roll (your own warbands are not killed).
# Approximated as +2 defense dice (since skulls hurt your own force).
def _outriders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    else:
        cs.campaign_defense_dice += 2
    return gs

register_effect(105, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_outriders_execute,
    description="Battle Plan: Ignore all skulls you roll (+2 dice approximation)",
))

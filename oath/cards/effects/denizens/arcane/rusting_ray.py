"""Rusting Ray (OATH-057) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import has_darkest_secret
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 58: Rusting Ray ───────────────────────────────────────────
# Battle Plan: If holding Darkest Secret, ignore hollow swords.
# Simplified: +2 attack dice if holding DS.
def _rusting_ray_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    return gs

register_effect(58, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=has_darkest_secret,
    execute=_rusting_ray_execute,
    description="Battle Plan: +2 attack dice if holding Darkest Secret",
))

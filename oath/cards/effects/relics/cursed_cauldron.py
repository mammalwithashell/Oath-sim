"""Cursed Cauldron (OATH-212) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 219: Relic 9 (Cursed Cauldron, OATH-212) ─────────────────
# Battle Plan: If victorious, gain 1 warband per enemy killed
# Simplified: +2 attack dice
def _cursed_cauldron_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is not None:
        if cs.campaign_attacker == player_index:
            cs.campaign_attack_dice += 2
        elif cs.campaign_defender == player_index:
            cs.campaign_defense_dice += 2
    return gs

register_effect(219, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_cursed_cauldron_execute,
    description="Battle Plan: Gain warbands per enemy killed",
))

"""Encirclement (OATH-124) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 125: Encirclement ──────────────────────────────────────────
# Battle Plan: ±2 defense dice if your force is larger than your enemy's.
def _encirclement_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        # Attacker: apply only if attack force > defense force
        if cs.campaign_attack_dice > cs.campaign_defense_dice:
            cs.campaign_attack_dice += 2
    elif cs.campaign_defender == player_index:
        # Defender: apply only if defense force > attack force
        if cs.campaign_defense_dice > cs.campaign_attack_dice:
            cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    return gs

register_effect(125, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_encirclement_execute,
    description="Battle Plan: ± 2 defense dice (simplified from force-size condition)",
))

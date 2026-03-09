"""Shield Wall (OATH-108) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 109: Shield Wall ───────────────────────────────────────────
# Battle Plan: +2 attack dice. If defeated, kill all your force (mark via _modifier_bool)
def _shield_wall_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    # Mark that defeat kills all force
    gs._modifier_bool = True
    return gs

register_effect(109, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_shield_wall_execute,
    description="Battle Plan: +2 attack dice, if defeated kill all your force",
))

"""Mountain Giant (OATH-155) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 156: Mountain Giant ───────────────────────────────────────
# BATTLE_PLAN: +/-1 or +/-3 defense dice (simplified: +/-2 defense dice)
def _mountain_giant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    return gs

register_effect(156, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_mountain_giant_execute,
    description="Battle Plan: +/-2 defense dice",
))

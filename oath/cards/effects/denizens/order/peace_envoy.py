"""Peace Envoy (OATH-125) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 126: Peace Envoy ───────────────────────────────────────────
# Battle Plan: Give enemy 1 favor per die they rolled (simplified: -1 attack die)
def _peace_envoy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice = max(0, cs.campaign_attack_dice - 1)
    return gs

register_effect(126, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_peace_envoy_execute,
    description="Battle Plan: -1 attack die (simplified from favor-per-die)",
))

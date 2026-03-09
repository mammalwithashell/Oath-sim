"""Relic Hunter (OATH-126) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 127: Relic Hunter ──────────────────────────────────────────
# Battle Plan: +1 defense die per relic targeted (simplified: +1 defense die)
def _relic_hunter_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(127, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_relic_hunter_execute,
    description="Battle Plan: +1 defense die (simplified from per-relic-targeted)",
))

"""War Tortoise (OATH-187) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 188: War Tortoise ─────────────────────────────────────────
# Battle Plan: Ignore double results from enemy. Simplified: +2
# defense dice.
def _war_tortoise_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(188, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_war_tortoise_execute,
    description="Battle Plan: Ignore enemy doubles (+2 defense dice)",
))

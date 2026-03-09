"""Rangers (OATH-045) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 47: Rangers ───────────────────────────────────────────────
# Battle Plan: Ignore skulls, +2 defense dice if defense pool has 4+.
def _rangers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defense_dice >= 4:
        cs.campaign_defense_dice += 2
    return gs

register_effect(47, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_rangers_execute,
    description="Battle Plan: Ignore skulls, +2 defense dice if pool >= 4",
))

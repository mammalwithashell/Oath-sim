"""Hearts and Minds (OATH-138) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 139: Hearts and Minds ─────────────────────────────────────
# Battle Plan: As defender, instant victory (simplified: +5 defense dice).
def _hearts_and_minds_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    return cs.campaign_defender == player_index

def _hearts_and_minds_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 5
    return gs

register_effect(139, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_hearts_and_minds_condition,
    execute=_hearts_and_minds_execute,
    description="Battle Plan: +5 defense dice (instant victory as defender)",
))

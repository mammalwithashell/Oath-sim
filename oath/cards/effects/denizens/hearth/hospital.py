"""Hospital (OATH-149) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 150: Hospital ─────────────────────────────────────────────
# Battle Plan: Warbands placed on site instead of killed
# (simplified: +3 defense dice).
def _hospital_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 3
    return gs

register_effect(150, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_hospital_execute,
    description="Battle Plan: +3 defense dice (warbands saved to site)",
))

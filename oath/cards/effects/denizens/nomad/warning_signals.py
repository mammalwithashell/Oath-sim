"""Warning Signals (OATH-025) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 33: Warning Signals ───────────────────────────────────────
# BATTLE_PLAN: Move warbands between board and ruled site
# (simplified: +2 defense dice)
def _warning_signals_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(33, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_warning_signals_execute,
    description="Battle Plan: +2 defense dice (simplified warband move)",
))

"""Horse Archers (OATH-024) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 32: Horse Archers ─────────────────────────────────────────
# BATTLE_PLAN: +/-3 defense dice
def _horse_archers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 3
    return gs

register_effect(32, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_horse_archers_execute,
    description="Battle Plan: +/-3 defense dice",
))

"""Village Constable (OATH-132) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 133: Village Constable ────────────────────────────────────
# Battle Plan: ±2 defense dice, unless your enemy has the People's Favor.
def _village_constable_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Determine enemy
    if cs.campaign_attacker == player_index:
        enemy = cs.campaign_defender
    else:
        enemy = cs.campaign_attacker
    # Don't apply if enemy holds People's Favor
    if enemy is not None and gs.peoples_favor_holder == enemy:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    elif cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    return gs

register_effect(133, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_village_constable_execute,
    description="Battle Plan: ±2 defense dice (unless enemy has People's Favor)",
))

"""The Great Levy (OATH-137) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 138: The Great Levy ───────────────────────────────────────
# Battle Plan: ±3 defense dice and ignore skulls, unless enemy has People's Favor.
def _the_great_levy_execute(gs: 'GameState', player_index: int) -> 'GameState':
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
        cs.campaign_defense_dice += 3
    elif cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    return gs

register_effect(138, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_the_great_levy_execute,
    description="Battle Plan: ±3 defense dice, ignore skulls",
))

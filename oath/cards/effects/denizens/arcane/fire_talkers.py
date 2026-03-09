"""Fire Talkers (OATH-031) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import has_darkest_secret
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 37: Fire Talkers ──────────────────────────────────────────
# Battle Plan: +/- 3 defense dice if holding Darkest Secret.
def _fire_talkers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 3
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    return gs

register_effect(37, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=has_darkest_secret,
    execute=_fire_talkers_execute,
    description="Battle Plan: +/- 3 defense dice if holding Darkest Secret",
))

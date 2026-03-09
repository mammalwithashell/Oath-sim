"""Extra Provisions (OATH-048) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 49: Extra Provisions ──────────────────────────────────────
# Battle Plan: +2 dice (attack dice for attacker, defense dice for defender).
def _extra_provisions_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    else:
        cs.campaign_defense_dice += 2
    return gs

register_effect(49, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_extra_provisions_execute,
    description="Battle Plan: +2 dice",
))

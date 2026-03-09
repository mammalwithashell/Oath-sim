"""Slander (OATH-102) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 103: Slander ─────────────────────────────────────────────
# Battle Plan: If victorious and targeted pawn, burn all enemy favor.
# Simplified: +3 attack dice.
def _slander_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 3
    return gs

register_effect(103, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_slander_execute,
    description="Battle Plan: +3 attack dice (simplified from burn enemy favor if victorious)",
))

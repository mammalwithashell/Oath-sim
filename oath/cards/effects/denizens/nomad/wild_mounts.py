"""Wild Mounts (OATH-153) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 154: Wild Mounts ──────────────────────────────────────────
# BATTLE_PLAN: May discard Beast card instead of Nomad battle plans
# (simplified: +1 defense die)
def _wild_mounts_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(154, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_wild_mounts_execute,
    description="Battle Plan: +1 defense die (simplified Beast discard)",
))

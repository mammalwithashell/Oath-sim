"""Sticky Fire (OATH-211) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 19: Sticky Fire (OATH-211) ────────────────────────────────
# Battle Plan: If victorious, kill all warbands in enemy's force.
# Must give them favor if able.
def _sticky_fire_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Mark that sticky fire is active - will be resolved in campaign victory
    # For now, we set _modifier_bool as a flag
    gs._modifier_bool = True
    return gs

register_effect(19, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_sticky_fire_execute,
    description="Battle Plan: If victorious, kill all enemy warbands, give them favor",
))

"""Grasping Vines (OATH-178) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 179: Grasping Vines ───────────────────────────────────────
# Modifier(Travel): Enemies traveling from ruled site must kill 1
# warband. Sets _modifier_bool.
def _grasping_vines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(179, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_grasping_vines_execute,
    description="Travel: Enemies leaving ruled site must kill 1 warband",
))

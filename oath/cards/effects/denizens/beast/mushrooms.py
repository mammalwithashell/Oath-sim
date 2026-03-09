"""Mushrooms (OATH-183) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 184: Mushrooms ────────────────────────────────────────────
# Modifier(Search): Spend no supply but draw only 1 card.
# Sets _modifier_int = 0.
def _mushrooms_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(184, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_mushrooms_execute,
    description="Search: Spend no supply, draw only 1 card",
))

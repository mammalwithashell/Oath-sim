"""Pressgangs (OATH-006) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 18: Pressgangs (OATH-006) ──────────────────────────────────
# Muster Modifier: Can muster on cards that have favor or secrets on them
# This modifies muster eligibility - implemented as a MODIFIER that sets
# _modifier_bool to True if a card has favor/secrets on it
def _pressgangs_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(18, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_pressgangs_execute,
    description="Can muster on cards with favor or secrets",
))

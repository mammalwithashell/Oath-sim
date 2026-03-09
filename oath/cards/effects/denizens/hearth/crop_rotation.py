"""Crop Rotation (OATH-128) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 129: Crop Rotation ────────────────────────────────────────
# Modifier(Search): May discard denizen at site before playing
# (simplified: no-op).
def _crop_rotation_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op for RL.
    return gs

register_effect(129, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_crop_rotation_execute,
    description="Search: May discard denizen at site before playing (no-op)",
))

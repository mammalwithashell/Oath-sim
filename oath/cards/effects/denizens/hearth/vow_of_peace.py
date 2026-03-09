"""Vow of Peace (OATH-145) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 146: Vow of Peace ─────────────────────────────────────────
# Modifier(Campaign): Cannot campaign (simplified: no-op for RL).
def _vow_of_peace_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op for RL.
    return gs

register_effect(146, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_vow_of_peace_execute,
    description="Campaign: Cannot campaign (no-op for RL)",
))

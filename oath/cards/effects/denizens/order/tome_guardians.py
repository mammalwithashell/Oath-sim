"""Tome Guardians (OATH-110) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 111: Tome Guardians ────────────────────────────────────────
# Persistent: Enemies cannot target Darkest Secret (simplified: no-op for RL)
def _tome_guardians_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(111, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_tome_guardians_execute,
    description="Persistent: Enemies cannot target Darkest Secret (no-op)",
))

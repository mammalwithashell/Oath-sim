"""Jinx (OATH-068) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 69: Jinx ──────────────────────────────────────────────────
# Persistent: May reroll dice.
# Simplified: no-op.
def _jinx_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(69, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_jinx_execute,
    description="Persistent: May reroll dice (no-op in simulator)",
))

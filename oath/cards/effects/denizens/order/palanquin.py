"""Palanquin (OATH-107) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 108: Palanquin ─────────────────────────────────────────────
# Action: Travel for free (simplified: gain 2 supply)
def _palanquin_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(108, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_palanquin_execute,
    description="Action: Travel for free (gain 2 supply)",
))

"""Alchemist (OATH-009) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 11: Alchemist (OATH-009) ───────────────────────────────────
# Action: Gain 4 favor from any favor bank or banks.
def _alchemist_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 4)

register_effect(11, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_alchemist_execute,
    description="Action: Gain 4 favor from any banks",
))

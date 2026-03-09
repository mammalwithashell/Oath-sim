"""Dazzle (OATH-035) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 41: Dazzle ────────────────────────────────────────────────
# When Played: Discard all Hearth and Order cards at sites in region.
# Simplified: gain 2 favor.
def _dazzle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor(gs, player_index, 2)

register_effect(41, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_dazzle_execute,
    description="When Played: Gain 2 favor (simplified from discard Hearth/Order)",
))

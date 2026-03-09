"""Deed Writer (OATH-146) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 147: Deed Writer ──────────────────────────────────────────
# Action: Exchange sites (simplified: gain 2 favor).
def _deed_writer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(147, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_deed_writer_execute,
    description="Action: Gain 2 favor (exchange sites)",
))

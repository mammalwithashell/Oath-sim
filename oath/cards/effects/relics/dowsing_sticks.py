"""Dowsing Sticks (OATH-219) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 218: Relic 8 (Dowsing Sticks, OATH-219) ──────────────────
# Action: Draw a relic (simplified: gain 1 secret)
def _dowsing_sticks_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(218, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_dowsing_sticks_execute,
    description="Action: Draw a relic",
))

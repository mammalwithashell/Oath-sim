"""Messenger (OATH-105) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 106: Messenger ─────────────────────────────────────────────
# Action: Move warbands between board and ruled sites
# Simplified: gain 2 warbands (representing redistribution value)
def _messenger_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(106, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_messenger_execute,
    description="Action: Move warbands between board and ruled sites",
))

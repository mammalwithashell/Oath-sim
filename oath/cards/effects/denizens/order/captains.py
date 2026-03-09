"""Captains (OATH-115) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 116: Captains ──────────────────────────────────────────────
# Action: Campaign at any ruled site (simplified: gain 3 warbands)
def _captains_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(116, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_captains_execute,
    description="Action: Campaign at any ruled site (gain 3 warbands)",
))

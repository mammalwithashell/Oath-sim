"""Homesteaders (OATH-127) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 128: Homesteaders ─────────────────────────────────────────
# Action: Move adviser to site (simplified: gain 1 favor).
def _homesteaders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(128, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_homesteaders_execute,
    description="Action: Gain 1 favor (move adviser to site)",
))

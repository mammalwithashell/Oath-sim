"""Hospitality (OATH-171) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType, Suit
from oath.cards.effects._helpers import always_true, gain_favor

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 172: Hospitality ──────────────────────────────────────────
# MODIFIER(Travel): After traveling, gain 1 favor from matching bank
def _hospitality_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor(gs, player_index, 1, Suit.NOMAD)

register_effect(172, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_hospitality_execute,
    description="Travel: Gain 1 favor from Nomad bank after traveling",
))

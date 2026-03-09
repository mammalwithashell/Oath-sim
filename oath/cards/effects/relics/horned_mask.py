"""Horned Mask (OATH-216) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 216: Spirit Snare (OATH-216) ──────────────────────────────
# Relic: Horned Mask - Action: Swap faceup adviser with site card
# Simplified: gain 1 favor
def _spirit_snare_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(216, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_spirit_snare_execute,
    description="Action: Swap adviser with site card",
))

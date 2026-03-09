"""Vow of Obedience (OATH-121) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 122: Vow of Obedience ──────────────────────────────────────
# Rest: Take 1 favor from any bank
def _vow_of_obedience_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(122, CardEffect(
    trigger=EffectTrigger.REST,
    condition=always_true,
    execute=_vow_of_obedience_execute,
    description="Rest: Take 1 favor from any bank",
))

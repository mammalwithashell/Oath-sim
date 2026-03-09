"""Fallen Spire (OATH-208) — Edifice (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 227: Ancient City (Fallen Spire, OATH-208) ───────────────
# Action: Swap cards from discard with Dispossessed (simplified: gain 1 favor)
def _fallen_spire_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(227, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_fallen_spire_execute,
    description="Action: Swap cards from discard",
))

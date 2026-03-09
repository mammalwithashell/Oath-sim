"""Royal Ambitions (OATH-088) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 89: Royal Ambitions ──────────────────────────────────────
# When Played: If Exile ruling more sites than Chancellor, may become Citizen.
# Simplified: gain 2 supply.
def _royal_ambitions_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(89, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_royal_ambitions_execute,
    description="When Played: Gain 2 supply (simplified)",
))

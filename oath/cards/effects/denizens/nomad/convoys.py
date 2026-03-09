"""Convoys (OATH-151) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 152: Convoys ──────────────────────────────────────────────
# ACTION: Move discard pile between regions (simplified: gain 1 supply)
def _convoys_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(152, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_convoys_execute,
    description="Action: Gain 1 supply (simplified discard-pile move)",
))

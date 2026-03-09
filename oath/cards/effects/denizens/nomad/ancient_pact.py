"""Ancient Pact (OATH-166) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 167: Ancient Pact ─────────────────────────────────────────
# WHEN_PLAYED: May become Citizen by giving Chancellor Darkest Secret
# (simplified: gain 2 supply)
def _ancient_pact_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(167, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_ancient_pact_execute,
    description="When Played: Gain 2 supply (simplified citizenship pact)",
))

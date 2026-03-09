"""The Gathering (OATH-027) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 34: The Gathering ─────────────────────────────────────────
# WHEN_PLAYED: Players may negotiate (simplified: gain 2 favor)
def _the_gathering_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(34, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_the_gathering_execute,
    description="When Played: Gain 2 favor (simplified negotiation)",
))

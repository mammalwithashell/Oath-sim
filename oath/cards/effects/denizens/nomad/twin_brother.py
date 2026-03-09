"""Twin Brother (OATH-170) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 171: Twin Brother ─────────────────────────────────────────
# WHEN_PLAYED: May swap with Nomad adviser of another player
# (simplified: gain 1 favor)
def _twin_brother_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(171, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_twin_brother_execute,
    description="When Played: Gain 1 favor (simplified adviser swap)",
))

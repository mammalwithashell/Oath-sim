"""Salt the Earth (OATH-089) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 90: Salt the Earth ───────────────────────────────────────
# When Played: Discard all cards at site.
# Simplified: gain 3 favor.
def _salt_the_earth_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 3)

register_effect(90, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_salt_the_earth_execute,
    description="When Played: Gain 3 favor (simplified from discard all cards at site)",
))

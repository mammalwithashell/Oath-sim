"""A Small Favor (OATH-015) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 7: A Small Favor (OATH-015) ───────────────────────────────
# When Played: Gain four warbands.
def _a_small_favor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 4)

register_effect(7, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_a_small_favor_execute,
    description="When Played: Gain 4 warbands",
))

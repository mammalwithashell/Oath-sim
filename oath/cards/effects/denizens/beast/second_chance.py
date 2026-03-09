"""Second Chance (OATH-181) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 182: Second Chance ────────────────────────────────────────
# Action: Kill 1 warband on board of player with Order/Discord adviser to gain 1 warband.
def _second_chance_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 1)

register_effect(182, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_second_chance_execute,
    description="Action: Gain 1 warband (kill enemy warband with Order/Discord adviser)",
))

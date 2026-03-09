"""Wild Allies (OATH-198) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 199: Wild Allies ──────────────────────────────────────────
# Action: Campaign at site with Beast card. Simplified: gain 3 warbands.
def _wild_allies_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(199, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wild_allies_execute,
    description="Action: Campaign at Beast card site (gain 3 warbands)",
))

"""A Round of Ale (OATH-129) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_supply

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 130: A Round of Ale ───────────────────────────────────────
# Action: Return favor/secrets as in Rest (simplified: gain 2 supply).
def _a_round_of_ale_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(130, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_a_round_of_ale_execute,
    description="Action: Gain 2 Supply (return favor/secrets as in Rest)",
))

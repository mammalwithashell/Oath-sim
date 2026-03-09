"""Cup of Plenty (OATH-217) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 213: Cup of Plenty (OATH-217) ─────────────────────────────
# Trade Modifier: Spend no supply if trading with card matching advisers
def _cup_of_plenty_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(213, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_cup_of_plenty_execute,
    description="Trade: Spend no supply on cards matching advisers",
))

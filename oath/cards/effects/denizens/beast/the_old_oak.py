"""The Old Oak (OATH-042) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS, ModifierType, Suit
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 10: The Old Oak (OATH-042) ────────────────────────────────
# Trade Modifier: If trading for secrets, gain one more secret if
# you have any Beast advisers.
def _old_oak_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                return True
    return False

def _old_oak_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(10, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=_old_oak_condition,
    execute=_old_oak_execute,
    description="Trade: +1 secret if you have Beast advisers",
))

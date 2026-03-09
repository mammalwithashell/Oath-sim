"""Nature Worship (OATH-175) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS, Suit
from oath.cards.effects._helpers import always_true
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 176: Nature Worship ───────────────────────────────────────
# Battle Plan: ±1 defense die per Beast adviser.
def _nature_worship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    beast_count = 0
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                beast_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += beast_count
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += beast_count
    return gs

register_effect(176, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_nature_worship_execute,
    description="Battle Plan: ±1 defense die per Beast adviser",
))

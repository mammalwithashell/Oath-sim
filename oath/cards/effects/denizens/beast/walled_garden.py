"""Walled Garden (OATH-195) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.effects._helpers import always_true
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 196: Walled Garden ────────────────────────────────────────
# Battle Plan: ± defense dice per Beast card at sites if targeted.
def _walled_garden_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    pawn_site = gs.sites[player.pawn_site]
    beast_count = 0
    for slot in range(pawn_site.capacity):
        card_id = pawn_site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                beast_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += beast_count
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += beast_count
    return gs

register_effect(196, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_walled_garden_execute,
    description="Battle Plan: ± defense dice per Beast card at site",
))

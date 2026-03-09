"""Taming Charm (OATH-037) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.effects._helpers import gain_favor
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


def _taming_charm_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit in (Suit.BEAST, Suit.NOMAD):
                return True
    return False

def _taming_charm_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    # Discard first Beast or Nomad card found
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit in (Suit.BEAST, Suit.NOMAD):
                site.cards[slot] = None
                gs.discard_piles[int(site.region)].append(card_id)
                gs = gain_favor(gs, player_index, 2, card_data.suit)
                break
    return gs

register_effect(2, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_taming_charm_condition,
    execute=_taming_charm_execute,
    description="Action: Discard Beast/Nomad card at site for 2 favor",
))

"""Kindred Warriors (OATH-060) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES, Suit
from oath.cards.effects._helpers import always_true
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 61: Kindred Warriors ──────────────────────────────────────
# Battle Plan: Ignore skulls, +/- defense dice per other suit ruled.
def _kindred_warriors_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count distinct suits ruled by this player (excluding Arcane)
    ruled_suits = set()
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            # Count each unique suit of cards at ruled sites
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    from oath.cards.database import get_card
                    card_data = get_card(card_id)
                    if card_data.suit != Suit.ARCANE:
                        ruled_suits.add(card_data.suit)
    bonus = len(ruled_suits)
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += bonus
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - bonus)
    return gs

register_effect(61, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_kindred_warriors_execute,
    description="Battle Plan: Ignore skulls, +/- defense dice per other suit ruled",
))

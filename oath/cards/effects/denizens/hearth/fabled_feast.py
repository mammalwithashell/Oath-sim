"""Fabled Feast (OATH-136) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS, MAX_SITES, Suit
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 137: Fabled Feast ─────────────────────────────────────────
# When Played: Gain favor equal to Hearth cards you rule.
def _fabled_feast_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    hearth_count = 0
    # Count Hearth advisers
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.HEARTH:
                hearth_count += 1
    # Count Hearth cards at ruled sites
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.HEARTH:
                        hearth_count += 1
    if hearth_count > 0:
        gs = gain_favor_from_banks(gs, player_index, hearth_count)
    return gs

register_effect(137, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_fabled_feast_execute,
    description="When Played: Gain favor equal to Hearth cards you rule",
))

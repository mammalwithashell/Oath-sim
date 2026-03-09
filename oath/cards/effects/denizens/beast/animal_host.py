"""Animal Host (OATH-190) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES, Suit
from oath.cards.effects._helpers import always_true, gain_warbands
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 191: Animal Host ──────────────────────────────────────────
# When Played: Gain warbands equal to Beast cards at sites in region.
def _animal_host_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    region = gs.sites[player.pawn_site].region
    beast_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == region:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.BEAST:
                        beast_count += 1
    return gain_warbands(gs, player_index, beast_count)

register_effect(191, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_animal_host_execute,
    description="When Played: Gain warbands equal to Beast cards in region",
))

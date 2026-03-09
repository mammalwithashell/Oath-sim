"""Silver Tongue (OATH-092) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 93: Silver Tongue ────────────────────────────────────────
# Rest: Take 1 favor from bank matching card at site.
def _silver_tongue_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit is not None:
                bank_idx = int(card_data.suit)
                if gs.favor_banks[bank_idx] > 0:
                    return True
    return False

def _silver_tongue_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    # Take 1 favor from the first matching bank with available favor
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit is not None:
                bank_idx = int(card_data.suit)
                if gs.favor_banks[bank_idx] > 0:
                    gs.favor_banks[bank_idx] -= 1
                    gs.players[player_index].favor += 1
                    break
    return gs

register_effect(93, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_silver_tongue_condition,
    execute=_silver_tongue_execute,
    description="Rest: Take 1 favor from bank matching card at site",
))

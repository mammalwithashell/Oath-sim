"""Memory of Nature (OATH-191) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES, Suit
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 192: Memory of Nature ─────────────────────────────────────
# Action: Move X favor from any favor banks to Beast bank. X = Beast cards on the map.
def _memory_of_nature_condition(gs: 'GameState', player_index: int) -> bool:
    beast_idx = int(Suit.BEAST)
    # Check if any non-Beast bank has favor to move
    for i in range(len(gs.favor_banks)):
        if i != beast_idx and gs.favor_banks[i] > 0:
            # Check if any Beast cards exist on the map
            for s in range(MAX_SITES):
                site = gs.sites[s]
                if site.is_faceup:
                    for slot in range(site.capacity):
                        card_id = site.cards[slot]
                        if card_id is not None:
                            card_data = get_card(card_id)
                            if card_data.suit == Suit.BEAST:
                                return True
    return False

def _memory_of_nature_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Count Beast cards at ALL sites on the map
    beast_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.BEAST:
                        beast_count += 1
    # Move favor from non-Beast banks to Beast bank
    beast_idx = int(Suit.BEAST)
    remaining = beast_count
    for i in range(len(gs.favor_banks)):
        if i != beast_idx and remaining > 0:
            take = min(remaining, gs.favor_banks[i])
            gs.favor_banks[i] -= take
            gs.favor_banks[beast_idx] += take
            remaining -= take
    return gs

register_effect(192, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_memory_of_nature_condition,
    execute=_memory_of_nature_execute,
    description="Action: Move X favor from banks to Beast bank (X = Beast cards on map)",
))

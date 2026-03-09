"""Disgraced Captain (OATH-020) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 29: Disgraced Captain ────────────────────────────────────
# Battle Plan: +4 defense dice if targeting site with Order card.
def _disgraced_captain_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Check if any targeted site has an Order card
    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            site = gs.sites[site_idx]
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.ORDER:
                        return True
    return False

def _disgraced_captain_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 4
    return gs

register_effect(29, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_disgraced_captain_condition,
    execute=_disgraced_captain_execute,
    description="Battle Plan: +4 defense dice if targeting site with Order card",
))

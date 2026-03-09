"""Great Crusade (OATH-164) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS, MAX_SITES, Suit
from oath.cards.effects._helpers import always_true
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 165: Great Crusade ────────────────────────────────────────
# BATTLE_PLAN: +/- defense dice per Nomad card ruled
def _great_crusade_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count Nomad cards at ruled sites
    nomad_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.NOMAD:
                        nomad_count += 1
    # Also count Nomad advisers
    player = gs.players[player_index]
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.NOMAD:
                nomad_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - nomad_count)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += nomad_count
    return gs

register_effect(165, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_great_crusade_execute,
    description="Battle Plan: +/- defense dice per Nomad card ruled",
))

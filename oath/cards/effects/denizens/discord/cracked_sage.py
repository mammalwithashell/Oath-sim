"""Cracked Sage (OATH-083) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS, Suit
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 84: Cracked Sage ─────────────────────────────────────────
# Battle Plan: ±4 defense dice if enemy has Arcane adviser.
def _cracked_sage_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Determine the enemy
    if cs.campaign_attacker == player_index:
        enemy = cs.campaign_defender
    elif cs.campaign_defender == player_index:
        enemy = cs.campaign_attacker
    else:
        return False
    if enemy is None:
        return False
    # Check if enemy has an Arcane adviser
    enemy_player = gs.players[enemy]
    for slot in range(MAX_ADVISERS):
        card_id = enemy_player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.ARCANE:
                return True
    return False

def _cracked_sage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 4
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 4)
    return gs

register_effect(84, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_cracked_sage_condition,
    execute=_cracked_sage_execute,
    description="Battle Plan: ±4 defense dice if enemy has Arcane adviser",
))

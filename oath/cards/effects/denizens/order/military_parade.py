"""Military Parade (OATH-109) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_ADVISERS
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 110: Military Parade ───────────────────────────────────────
# Battle Plan: If victorious, gain 1 favor per enemy adviser suit
def _military_parade_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Determine enemy
    enemy_index = None
    if cs.campaign_attacker == player_index:
        enemy_index = cs.campaign_defender
    elif cs.campaign_defender == player_index:
        enemy_index = cs.campaign_attacker
    if enemy_index is None:
        return gs
    # Count enemy adviser suits
    enemy = gs.players[enemy_index]
    suit_count = 0
    for i in range(MAX_ADVISERS):
        if enemy.advisers[i] is not None:
            card_data = get_card(enemy.advisers[i])
            if card_data.suit is not None:
                suit_count += 1
    if suit_count > 0:
        gs = gain_favor_from_banks(gs, player_index, suit_count)
    return gs

register_effect(110, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_military_parade_execute,
    description="Battle Plan: Gain 1 favor per enemy adviser suit",
))

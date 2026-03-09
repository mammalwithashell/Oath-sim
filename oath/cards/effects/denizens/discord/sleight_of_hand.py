"""Sleight of Hand (OATH-017) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 27: Sleight of Hand ──────────────────────────────────────
# Action: Take 1 secret from player at your site.
# Condition: another player at site with >1 secret.
def _sleight_of_hand_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for i in range(gs.num_players):
        if i != player_index and gs.players[i].pawn_site == player.pawn_site:
            if gs.players[i].secrets > 1:
                return True
    return False

def _sleight_of_hand_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Take 1 secret from the first eligible player at the same site
    for i in range(gs.num_players):
        if i != player_index and gs.players[i].pawn_site == player.pawn_site:
            if gs.players[i].secrets > 1:
                gs.players[i].secrets -= 1
                gs.players[player_index].secrets += 1
                break
    return gs

register_effect(27, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_sleight_of_hand_condition,
    execute=_sleight_of_hand_execute,
    description="Action: Take 1 secret from player at your site",
))

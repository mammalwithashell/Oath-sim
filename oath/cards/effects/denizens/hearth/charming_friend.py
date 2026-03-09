"""Charming Friend (OATH-131) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 132: Charming Friend ──────────────────────────────────────
# Action: Take 1 favor from player at your site.
def _charming_friend_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site and p.favor > 0:
            return True
    return False

def _charming_friend_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Take 1 favor from the first other player at the same site who has favor
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site and p.favor > 0:
            p.favor -= 1
            player.favor += 1
            break
    return gs

register_effect(132, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_charming_friend_condition,
    execute=_charming_friend_execute,
    description="Action: Take 1 favor from player at your site",
))

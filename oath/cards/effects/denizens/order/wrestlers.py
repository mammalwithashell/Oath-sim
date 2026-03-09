"""Wrestlers (OATH-001) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 17: Wrestlers (OATH-001) ──────────────────────────────────
# Battle Plan: +1 attack die if you sacrifice one warband in your force.
def _wrestlers_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board > 0

def _wrestlers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    if player.warbands_board > 0:
        player.warbands_board -= 1
        site = gs.sites[player.pawn_site]
        if site.warbands > 0:
            site.warbands -= 1
        cs.campaign_attack_dice += 1
    return gs

register_effect(17, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_wrestlers_condition,
    execute=_wrestlers_execute,
    description="Battle Plan: Sacrifice 1 warband for +1 attack die",
))

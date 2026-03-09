"""Keep (OATH-005) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 15: Keep (OATH-005) ────────────────────────────────────────
# Battle Plan: +2 attack dice if this site is targeted
def _keep_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Keep is a site-only card, check if any targeted site has the Keep
    return cs.campaign_defender == player_index

def _keep_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # +2 defense dice if defender's site is targeted
    player = gs.players[player_index]
    pawn_site = player.pawn_site
    for target in cs.campaign_targets:
        if target == f"site:{pawn_site}":
            cs.campaign_defense_dice += 2
            break
    return gs

register_effect(15, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_keep_condition,
    execute=_keep_execute,
    description="Battle Plan: +2 defense dice if this site is targeted",
))

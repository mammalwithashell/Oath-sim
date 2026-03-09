"""Bear Traps (OATH-003) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 13: Bear Traps (OATH-003) ─────────────────────────────────
# Battle Plan: -1 defense die AND kill one warband on attacker's board.
def _bear_traps_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # -1 defense die (reduces attacker's attack effectiveness)
    cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 1)
    # Kill 1 warband on the attacker's board
    if cs.campaign_attacker is not None:
        attacker = gs.players[cs.campaign_attacker]
        if attacker.warbands_board > 0:
            attacker.warbands_board -= 1
            attacker_site = gs.sites[attacker.pawn_site]
            if attacker_site.warbands > 0:
                attacker_site.warbands -= 1
    return gs

register_effect(13, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_bear_traps_execute,
    description="Battle Plan: Kill 1 attacker warband",
))

"""Garrison (OATH-007) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES
from oath.cards.effects._helpers import always_true, count_ruled_sites, gain_warbands

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 8: Garrison (OATH-007) ─────────────────────────────────────
# When Played: gain one warband per site you rule, put one warband
# from your board on each site you rule.
def _garrison_execute(gs: 'GameState', player_index: int) -> 'GameState':
    ruled = count_ruled_sites(gs, player_index)
    gs = gain_warbands(gs, player_index, ruled)
    # Place one warband from board on each ruled site
    player = gs.players[player_index]
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            if player.warbands_board > 0:
                player.warbands_board -= 1
                site.warbands += 1
    return gs

register_effect(8, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_garrison_execute,
    description="When Played: gain warbands per ruled site, place on each",
))

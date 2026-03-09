"""Siege Engines (OATH-116) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 117: Siege Engines ─────────────────────────────────────────
# Action: Kill 2 warbands at any site in region
def _siege_engines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_region = gs.sites[player.pawn_site].region
    # Kill 2 warbands at the site in the region with the most enemy warbands
    best_site = None
    best_warbands = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == pawn_region and site.warbands > 0:
            if site.ruling_player != player_index and site.warbands > best_warbands:
                best_site = i
                best_warbands = site.warbands
    if best_site is not None:
        site = gs.sites[best_site]
        killed = min(2, site.warbands)
        site.warbands -= killed
        # Find the ruling player to update their board count
        if site.ruling_player is not None:
            gs.players[site.ruling_player].warbands_board -= killed
        if site.warbands <= 0:
            site.warbands = 0
            site.ruling_player = None
            site.warband_color = None
    return gs

register_effect(117, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_siege_engines_execute,
    description="Action: Kill 2 warbands at any site in region",
))

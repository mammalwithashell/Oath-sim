"""Terror Spells (OATH-061) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import has_darkest_secret
from oath.enums import EffectTrigger, MAX_SITES

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 62: Terror Spells ─────────────────────────────────────────
# Action: Kill 2 warbands in region if holding Darkest Secret.
def _terror_spells_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_site = gs.sites[player.pawn_site]
    region = pawn_site.region
    kills_remaining = 2
    for i in range(MAX_SITES):
        if kills_remaining <= 0:
            break
        site = gs.sites[i]
        if site.region == region and site.is_faceup:
            # Kill warbands belonging to other players at this site
            for pi in range(len(gs.players)):
                if pi == player_index or kills_remaining <= 0:
                    continue
                # Simplified: reduce site warbands and player board warbands
                kill = min(kills_remaining, site.warbands)
                if kill > 0:
                    site.warbands -= kill
                    gs.players[pi].warbands_board -= min(kill, gs.players[pi].warbands_board)
                    kills_remaining -= kill
                    if site.warbands <= 0:
                        site.warbands = 0
                        site.ruling_player = None
                        site.warband_color = None
    return gs

register_effect(62, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=has_darkest_secret,
    execute=_terror_spells_execute,
    description="Action: Kill 2 warbands in region (requires Darkest Secret)",
))

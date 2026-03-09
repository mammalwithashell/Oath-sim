"""Royal Tax (OATH-117) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 118: Royal Tax ─────────────────────────────────────────────
# When Played: Take 2 favor from each player at your ruled sites in region
def _royal_tax_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_region = gs.sites[player.pawn_site].region
    # Find all players at ruled sites in same region
    taxed_players = set()
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == pawn_region and site.ruling_player == player_index:
            for pi, p in enumerate(gs.players):
                if pi != player_index and p.pawn_site == i:
                    taxed_players.add(pi)
    for pi in taxed_players:
        taken = min(2, gs.players[pi].favor)
        gs.players[pi].favor -= taken
        gs.players[player_index].favor += taken
    return gs

register_effect(118, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_royal_tax_execute,
    description="When Played: Take 2 favor from each player at ruled sites in region",
))

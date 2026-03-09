"""Witch's Bargain (OATH-077) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import has_secrets_and_player_at_site

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 78: Witch's Bargain ───────────────────────────────────────
# Action: Give secret to player at site, take 2 favor.
def _witchs_bargain_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Give 1 secret to another player at the same site
    for pi in range(len(gs.players)):
        if pi != player_index and gs.players[pi].pawn_site == player.pawn_site:
            player.secrets -= 1
            gs.players[pi].secrets += 1
            break
    # Take 2 favor from that player (simplified: just gain 2 favor)
    player.favor += 2
    return gs

register_effect(78, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=has_secrets_and_player_at_site,
    execute=_witchs_bargain_execute,
    description="Action: Give 1 secret to player at site, take 2 favor",
))

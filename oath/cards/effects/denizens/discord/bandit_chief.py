"""Bandit Chief (OATH-100) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, MAX_SITES
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 101: Bandit Chief ────────────────────────────────────────
# When Played: Kill 1 warband at each site.
def _bandit_chief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.warbands > 0:
            site.warbands -= 1
            if site.ruling_player is not None:
                gs.players[site.ruling_player].warbands_board = max(
                    0, gs.players[site.ruling_player].warbands_board - 1)
            if site.warbands <= 0:
                site.warbands = 0
                site.ruling_player = None
                site.warband_color = None
    return gs

register_effect(101, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_bandit_chief_execute,
    description="When Played: Kill 1 warband at each site",
))

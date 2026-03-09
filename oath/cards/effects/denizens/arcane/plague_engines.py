"""Plague Engines (OATH-065) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.effects._helpers import always_true, count_ruled_sites

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 66: Plague Engines ────────────────────────────────────────
# Action: Each player places 1 favor per site ruled into Arcane bank.
def _plague_engines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for pi in range(len(gs.players)):
        ruled = count_ruled_sites(gs, pi)
        if ruled > 0:
            player = gs.players[pi]
            transfer = min(ruled, player.favor)
            player.favor -= transfer
            gs.favor_banks[int(Suit.ARCANE)] += transfer
    return gs

register_effect(66, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_plague_engines_execute,
    description="Action: Each player places 1 favor per ruled site into Arcane bank",
))

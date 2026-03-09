"""Book Burning (OATH-022) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 30: Book Burning ─────────────────────────────────────────
# Battle Plan: If victorious and targeted pawn, burn enemy's secrets.
# Simplified: +2 attack dice.
def _book_burning_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(30, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_book_burning_execute,
    description="Battle Plan: +2 attack dice (simplified from burn enemy secrets if victorious)",
))

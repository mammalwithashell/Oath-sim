"""Chaos Cult (OATH-101) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 102: Chaos Cult ──────────────────────────────────────────
# Persistent: After player takes Oathkeeper, take favor from them.
# Simplified: no-op.
def _chaos_cult_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(102, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_chaos_cult_execute,
    description="Persistent: Take favor from new Oathkeeper (no-op)",
))

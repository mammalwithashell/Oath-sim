"""Relic Thief (OATH-095) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 96: Relic Thief ──────────────────────────────────────────
# Persistent: After player takes relics in your region, may steal.
# Simplified: no-op.
def _relic_thief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(96, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_relic_thief_execute,
    description="Persistent: May steal relics taken in your region (no-op)",
))

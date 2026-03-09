"""Gossip (OATH-099) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 100: Gossip ──────────────────────────────────────────────
# Persistent: Enemies can't play cards as facedown advisers.
# Simplified: no-op.
def _gossip_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(100, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_gossip_execute,
    description="Persistent: Enemies can't play facedown advisers (no-op)",
))

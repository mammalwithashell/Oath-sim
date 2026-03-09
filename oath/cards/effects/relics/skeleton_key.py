"""Skeleton Key (OATH-223) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 215: Skeleton Key (OATH-223) ──────────────────────────────
# Action: Peek at relic in Reliquary, may take it (simplified: gain 1 secret)
def _skeleton_key_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(215, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_skeleton_key_execute,
    description="Action: Peek at Reliquary relic",
))

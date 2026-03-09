"""Ivory Eye (OATH-226) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 212: Ivory Eye (OATH-226) ─────────────────────────────────
# Action: Peek at any facedown site/adviser/relic (no-op for RL)
def _ivory_eye_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(212, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ivory_eye_execute,
    description="Action: Peek at facedown card",
))

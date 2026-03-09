"""Squalid District (OATH-206) — Edifice (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 228: Fallen Monastery (Squalid District, OATH-206) ───────
# Ruler may adjust game-end die roll (simplified: no-op)
register_effect(228, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Ruler may adjust end-game die roll",
))

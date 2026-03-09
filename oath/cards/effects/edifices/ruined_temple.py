"""Ruined Temple (OATH-204) — Edifice (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 229: Ruined Tower (Ruined Temple, OATH-204) ──────────────
# Enemies can't play Beast cards faceup (simplified: no-op)
register_effect(229, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Enemies can't play Beast cards faceup",
))

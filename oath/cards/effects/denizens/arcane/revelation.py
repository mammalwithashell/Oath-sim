"""Revelation (OATH-063) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 64: Revelation ────────────────────────────────────────────
# When Played: Players may burn favor to gain secrets.
# Simplified: gain 1 secret.
def _revelation_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(64, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_revelation_execute,
    description="When Played: Gain 1 secret (simplified from burn favor for secrets)",
))

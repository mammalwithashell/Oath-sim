"""Bewitch (OATH-067) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 68: Bewitch ───────────────────────────────────────────────
# When Played: If Exile with more secrets than Chancellor, may become Citizen.
# Simplified: gain 2 secrets.
def _bewitch_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 2)

register_effect(68, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_bewitch_execute,
    description="When Played: Gain 2 secrets (simplified from citizenship swap)",
))

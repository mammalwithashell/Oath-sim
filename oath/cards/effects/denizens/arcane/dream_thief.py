"""Dream Thief (OATH-070) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 71: Dream Thief ───────────────────────────────────────────
# Action: Swap 2 facedown advisers.
# Simplified: gain 1 secret.
def _dream_thief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(71, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_dream_thief_execute,
    description="Action: Gain 1 secret (simplified from swap advisers)",
))

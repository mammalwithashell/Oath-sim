"""Insomnia (OATH-097) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 98: Insomnia ─────────────────────────────────────────────
# Rest: Gain 1 secret.
def _insomnia_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(98, CardEffect(
    trigger=EffectTrigger.REST,
    condition=always_true,
    execute=_insomnia_execute,
    description="Rest: Gain 1 secret",
))

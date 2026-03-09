"""Spell Breaker (OATH-162) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 163: Spell Breaker ────────────────────────────────────────
# PERSISTENT: Enemies can't use powers costing secrets (simplified: no-op)
def _spell_breaker_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(163, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_spell_breaker_execute,
    description="Persistent: Block enemy secret-cost powers (no-op)",
))

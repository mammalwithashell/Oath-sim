"""Secret Signal (OATH-055) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 56: Secret Signal ─────────────────────────────────────────
# Modifier(Trade): If gain only 1 favor, gain 1 more.
# Simplified: set _modifier_int += 1.
def _secret_signal_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(56, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_secret_signal_execute,
    description="Trade: +1 favor if gaining only 1",
))

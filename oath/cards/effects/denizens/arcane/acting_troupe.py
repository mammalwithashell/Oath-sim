"""Acting Troupe (OATH-036) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 42: Acting Troupe ─────────────────────────────────────────
# Modifier(Trade): Act as if card is Beast or Order.
# Simplified: set _modifier_bool.
def _acting_troupe_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(42, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_acting_troupe_execute,
    description="Trade: Act as if card is Beast or Order",
))

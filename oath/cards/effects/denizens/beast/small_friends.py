"""Small Friends (OATH-177) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 178: Small Friends ────────────────────────────────────────
# Modifier(Trade): Act as if pawn at any site with Beast card.
# Simplified: no-op.
def _small_friends_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(178, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_small_friends_execute,
    description="Trade: Act as if pawn at site with Beast card (no-op)",
))

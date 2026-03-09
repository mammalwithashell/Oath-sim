"""Birdsong (OATH-176) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 177: Birdsong ─────────────────────────────────────────────
# Modifier(Trade): Spend no supply if trading with Beast or Nomad card.
def _birdsong_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(177, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_birdsong_execute,
    description="Trade: Spend no supply if trading with Beast/Nomad card",
))

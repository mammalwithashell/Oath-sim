"""Bracken (OATH-197) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 198: Bracken ──────────────────────────────────────────────
# Modifier(Search): Put discards on top/bottom of any discard pile.
# Simplified: no-op.
def _bracken_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(198, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_bracken_execute,
    description="Search: Rearrange discard pile (no-op)",
))

"""Observatory (OATH-064) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 65: Observatory ───────────────────────────────────────────
# Modifier(Search): May draw from any discard pile.
# Simplified: set _modifier_bool.
def _observatory_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(65, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_observatory_execute,
    description="Search: May draw from any discard pile",
))

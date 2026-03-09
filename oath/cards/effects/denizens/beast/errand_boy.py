"""Errand Boy (OATH-011) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 9: Errand Boy (OATH-011) ──────────────────────────────────
# Search Modifier: May draw from a discard pile in a different region.
# This modifies search behavior - sets _modifier_bool to signal
# cross-region discard search is allowed.
def _errand_boy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(9, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_errand_boy_execute,
    description="Search: May draw from other region's discard pile",
))

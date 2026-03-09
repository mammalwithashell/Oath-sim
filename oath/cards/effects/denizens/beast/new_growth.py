"""New Growth (OATH-188) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 189: New Growth ───────────────────────────────────────────
# Modifier(Search): May play Beast/Hearth cards to any site.
# Simplified: set _modifier_bool.
def _new_growth_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(189, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_new_growth_execute,
    description="Search: May play Beast/Hearth cards to any site",
))

"""Forest Paths (OATH-043) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


def _forest_paths_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Check if the travel target site has a Beast card
    # The target site index is stored contextually during travel_cost computation
    # We use _modifier_int which holds the current cost
    # We need to check target site - since we're called from travel_cost,
    # we check all sites for beast cards at the target
    # For simplicity: set cost to 0 if target has beast card
    # The target site is not directly passed, but we can check _modifier_bool
    # as a flag. Actually, we need a different approach.
    # Set _modifier_bool to signal that beast-site travel is free.
    gs._modifier_bool = True
    return gs

register_effect(4, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_forest_paths_execute,
    description="Travel: Free travel to sites with Beast cards",
))

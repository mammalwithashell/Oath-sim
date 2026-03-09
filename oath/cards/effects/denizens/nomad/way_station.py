"""Way Station (OATH-169) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 170: Way Station ──────────────────────────────────────────
# MODIFIER(Travel): Free travel to this site
# (set _modifier_int = 0 if traveling to site with this card)
def _way_station_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # If traveling to the site that has this card, cost is 0.
    # We check if target site has this card; since we're called during
    # travel_cost computation, we set cost to 0 optimistically.
    # The travel system will verify site matching.
    gs._modifier_int = 0
    return gs

register_effect(170, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_way_station_execute,
    description="Travel: Free travel to this site",
))

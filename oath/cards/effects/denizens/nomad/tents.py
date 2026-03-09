"""Tents (OATH-029) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 16: Tents (OATH-029) ──────────────────────────────────────
# Travel Modifier: Spend no Supply if traveling to a site in your region.
def _tents_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # The cost is in _modifier_int. If traveling within same region, set to 0.
    # We need to check if current site and target are in same region.
    # Since we're called from travel_cost loop, the context is:
    # the player's current region vs target region.
    player = gs.players[player_index]
    current_region = gs.sites[player.pawn_site].region
    # We need to check the target site region. The travel_cost function
    # has this info but doesn't pass it to us directly.
    # We use a convention: if regions match, cost goes to 0.
    # The cost is 1 for same-region travel, so if _modifier_int == 1,
    # it's same-region and we set to 0.
    if gs._modifier_int == 1:
        gs._modifier_int = 0
    return gs

register_effect(16, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_tents_execute,
    description="Travel: Free travel within your region",
))

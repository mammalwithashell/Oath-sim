"""Boiling Lake (OATH-094) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 95: Boiling Lake ─────────────────────────────────────────
# Modifier(Travel): If traveling to site and don't rule, must kill 2 warbands.
# Set _modifier_bool to signal travel penalty.
def _boiling_lake_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(95, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_boiling_lake_execute,
    description="Travel: Must kill 2 warbands if traveling to site you don't rule",
))

"""Downtrodden (OATH-081) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 82: Downtrodden ──────────────────────────────────────────
# Modifier(Muster): Gain 2 more warbands if mustering on card whose bank
# has least favor.
def _downtrodden_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Add 2 extra warbands via modifier int
    gs._modifier_int += 2
    return gs

register_effect(82, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_downtrodden_execute,
    description="Muster: Gain 2 more warbands if mustering on least-favor bank card",
))

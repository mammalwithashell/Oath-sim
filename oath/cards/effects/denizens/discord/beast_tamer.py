"""Beast Tamer (OATH-090) — Denizen (Discord)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 91: Beast Tamer ──────────────────────────────────────────
# Modifier(Campaign): Enemies can't use Beast/Nomad battle plans.
# Simplified: +1 defense die.
def _beast_tamer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(91, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_beast_tamer_execute,
    description="Campaign: +1 defense die (simplified from block Beast/Nomad battle plans)",
))

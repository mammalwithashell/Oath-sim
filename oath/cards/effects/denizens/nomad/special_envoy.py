"""Special Envoy (OATH-158) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 159: Special Envoy ────────────────────────────────────────
# MODIFIER(Travel): Spend no supply, end Act Phase after
# (set _modifier_int = 0)
def _special_envoy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(159, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_special_envoy_execute,
    description="Travel: Spend no supply (ends Act Phase after)",
))

"""Saddle Makers (OATH-142) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 143: Saddle Makers ────────────────────────────────────────
# Modifier(Search): When Nomad/Order played, gain 2 favor from matching bank.
def _saddle_makers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(143, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_saddle_makers_execute,
    description="Search: Gain 2 favor when Nomad/Order card played",
))

"""Magician's Code (OATH-032) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 38: Magician's Code ───────────────────────────────────────
# Modifier(Recover): If recovering Darkest Secret, gain 2 secrets.
# Simplified: gain 2 secrets when condition met.
def _magicians_code_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_secrets(gs, player_index, 2)
    return gs

register_effect(38, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_magicians_code_execute,
    description="Recover: Gain 2 secrets when recovering Darkest Secret",
))

"""Wizard School (OATH-034) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 40: Wizard School ─────────────────────────────────────────
# Action: Gain 1 secret, then end Act Phase.
# Simplified: gain 1 secret.
def _wizard_school_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(40, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wizard_school_execute,
    description="Action: Gain 1 secret (ends Act Phase)",
))

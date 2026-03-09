"""Storyteller (OATH-052) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 53: Storyteller ───────────────────────────────────────────
# Action: Place 1 secret from shared bank on Darkest Secret
# (simplified: gain 1 secret).
def _storyteller_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(53, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_storyteller_execute,
    description="Action: Gain 1 secret (place on Darkest Secret)",
))

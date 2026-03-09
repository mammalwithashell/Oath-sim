"""Resettle (OATH-159) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 160: Resettle ─────────────────────────────────────────────
# ACTION: Move Nomad card between sites/advisers
# (simplified: gain 1 favor)
def _resettle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(160, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_resettle_execute,
    description="Action: Gain 1 favor (simplified Nomad card move)",
))

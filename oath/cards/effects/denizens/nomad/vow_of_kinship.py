"""Vow of Kinship (OATH-152) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 153: Vow of Kinship ───────────────────────────────────────
# PERSISTENT: Favor goes to Nomad bank (simplified: no-op)
def _vow_of_kinship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(153, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_kinship_execute,
    description="Persistent: Favor goes to Nomad bank (no-op)",
))

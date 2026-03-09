"""Ancient Bloodline (OATH-165) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 166: Ancient Bloodline ────────────────────────────────────
# PERSISTENT: Enemies treat ruled denizens/relics as locked
# (simplified: no-op)
def _ancient_bloodline_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(166, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_ancient_bloodline_execute,
    description="Persistent: Lock ruled denizens/relics from enemies (no-op)",
))

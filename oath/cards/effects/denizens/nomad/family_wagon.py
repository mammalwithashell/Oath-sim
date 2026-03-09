"""Family Wagon (OATH-168) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 169: Family Wagon ─────────────────────────────────────────
# PERSISTENT: Only 1 non-Nomad adviser, unlimited Nomad
# (simplified: no-op)
def _family_wagon_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(169, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_family_wagon_execute,
    description="Persistent: Unlimited Nomad advisers (no-op)",
))

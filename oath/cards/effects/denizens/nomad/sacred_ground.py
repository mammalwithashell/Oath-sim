"""Sacred Ground (OATH-174) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 175: Sacred Ground ────────────────────────────────────────
# MODIFIER(Search): Players can't play Visions faceup unless at this
# site (simplified: no-op)
def _sacred_ground_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(175, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_sacred_ground_execute,
    description="Search: Restrict Vision play to this site (no-op)",
))

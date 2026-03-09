"""Secret Police (OATH-113) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 114: Secret Police ─────────────────────────────────────────
# Persistent: Enemies can't play Visions faceup at ruler's sites (simplified: no-op)
def _secret_police_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(114, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_secret_police_execute,
    description="Persistent: Enemies can't play Visions faceup at ruler's sites (no-op)",
))

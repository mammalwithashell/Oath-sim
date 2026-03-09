"""Forest Council (OATH-194) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 195: Forest Council ───────────────────────────────────────
# Persistent: Enemies can't trade with Beast cards. Simplified: no-op.
def _forest_council_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(195, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_forest_council_execute,
    description="Persistent: Enemies can't trade with Beast cards (no-op)",
))

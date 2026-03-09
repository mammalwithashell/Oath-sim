"""Lost Tongue (OATH-157) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 158: Lost Tongue ──────────────────────────────────────────
# PERSISTENT: Others can't target your relics/banners unless ruling
# Nomad card (simplified: no-op)
def _lost_tongue_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(158, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_lost_tongue_execute,
    description="Persistent: Protect relics/banners (no-op)",
))

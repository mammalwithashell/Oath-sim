"""Book of Records (OATH-229) — Relic."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 214: Book of Records (OATH-229) ───────────────────────────
# Persistent: Must gain secrets instead of favor when playing to site
# Simplified: no-op for RL
register_effect(214, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Must gain secrets instead of favor when playing to site",
))

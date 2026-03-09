"""Family Heirloom (OATH-133) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 134: Family Heirloom ──────────────────────────────────────
# When Played: Draw a relic (simplified: gain 1 secret).
def _family_heirloom_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(134, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_family_heirloom_execute,
    description="When Played: Gain 1 secret (draw a relic)",
))

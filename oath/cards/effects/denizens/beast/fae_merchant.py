"""Fae Merchant (OATH-180) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_secrets

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 181: Fae Merchant ─────────────────────────────────────────
# Action: Draw a relic and take it. Simplified: gain 1 secret.
def _fae_merchant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(181, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_fae_merchant_execute,
    description="Action: Draw and take relic (gain 1 secret)",
))

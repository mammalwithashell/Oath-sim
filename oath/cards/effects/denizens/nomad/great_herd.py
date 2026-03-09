"""Great Herd (OATH-030) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 36: Great Herd ────────────────────────────────────────────
# WHEN_PLAYED: May swap with Nomad card at any site
# (simplified: gain 1 favor)
def _great_herd_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(36, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_great_herd_execute,
    description="When Played: Gain 1 favor (simplified swap)",
))

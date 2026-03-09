"""Spirit Snare (OATH-033) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 39: Spirit Snare ──────────────────────────────────────────
# Action: Take 1 favor from any bank.
def _spirit_snare_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(39, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_spirit_snare_execute,
    description="Action: Take 1 favor from any bank",
))

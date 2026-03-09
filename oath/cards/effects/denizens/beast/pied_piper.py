"""Pied Piper (OATH-182) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 183: Pied Piper ───────────────────────────────────────────
# Action: Move card to another player's advisers, take 2 favor from
# them. Simplified: gain 2 favor.
def _pied_piper_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(183, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_pied_piper_execute,
    description="Action: Move card to other player's advisers (gain 2 favor)",
))

"""Ballot Box (OATH-141) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 142: Ballot Box ───────────────────────────────────────────
# Action: If Exile with People's Favor, become Citizen
# (simplified: gain 2 favor).
def _ballot_box_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(142, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ballot_box_execute,
    description="Action: Gain 2 favor (become Citizen if Exile with People's Favor)",
))

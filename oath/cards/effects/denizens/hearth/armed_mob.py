"""Armed Mob (OATH-053) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 54: Armed Mob ─────────────────────────────────────────────
# Action: Discard a faceup adviser from Darkest Secret holder
# (simplified: gain 1 favor).
def _armed_mob_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(54, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_armed_mob_execute,
    description="Action: Gain 1 favor (discard adviser from DS holder)",
))

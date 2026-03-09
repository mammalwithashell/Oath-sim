"""Salad Days (OATH-147) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 148: Salad Days ───────────────────────────────────────────
# When Played: Gain 3 favor from 3 different banks.
def _salad_days_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Take 1 favor from each of the 3 largest banks
    banks = gs.favor_banks
    # Get bank indices sorted by amount descending
    sorted_banks = sorted(range(len(banks)), key=lambda i: banks[i], reverse=True)
    taken = 0
    for bank_idx in sorted_banks:
        if taken >= 3:
            break
        if banks[bank_idx] > 0:
            banks[bank_idx] -= 1
            gs.players[player_index].favor += 1
            taken += 1
    return gs

register_effect(148, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_salad_days_execute,
    description="When Played: Gain 3 favor from 3 different banks",
))

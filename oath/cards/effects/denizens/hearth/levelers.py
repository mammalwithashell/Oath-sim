"""Levelers (OATH-135) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 136: Levelers ─────────────────────────────────────────────
# Action: Move 2 favor from largest bank to smallest.
def _levelers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    banks = gs.favor_banks
    largest_idx = max(range(len(banks)), key=lambda i: banks[i])
    smallest_idx = min(range(len(banks)), key=lambda i: banks[i])
    if largest_idx != smallest_idx and banks[largest_idx] > 0:
        transfer = min(2, banks[largest_idx])
        banks[largest_idx] -= transfer
        banks[smallest_idx] += transfer
    return gs

register_effect(136, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_levelers_execute,
    description="Action: Move 2 favor from largest bank to smallest",
))

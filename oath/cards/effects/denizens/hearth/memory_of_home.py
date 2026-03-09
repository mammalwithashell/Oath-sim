"""Memory of Home (OATH-049) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 50: Memory of Home ────────────────────────────────────────
# Action: Move all favor from one bank to Hearth bank.
def _memory_of_home_execute(gs: 'GameState', player_index: int) -> 'GameState':
    hearth_idx = int(Suit.HEARTH)
    # Find the largest non-Hearth bank and move all its favor to Hearth
    best_bank = -1
    best_amount = 0
    for i in range(len(gs.favor_banks)):
        if i != hearth_idx and gs.favor_banks[i] > best_amount:
            best_amount = gs.favor_banks[i]
            best_bank = i
    if best_bank >= 0 and best_amount > 0:
        gs.favor_banks[hearth_idx] += best_amount
        gs.favor_banks[best_bank] = 0
    return gs

register_effect(50, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_memory_of_home_execute,
    description="Action: Move all favor from one bank to Hearth bank",
))

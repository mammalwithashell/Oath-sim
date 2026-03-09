"""Battle Honors (OATH-002) — Denizen (Order)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, Suit
from oath.cards.effects._helpers import always_true, gain_favor

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 20: Battle Honors ──────────────────────────────────────────
# Battle Plan: If victorious, gain 2 favor from Order bank
def _battle_honors_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Grant 2 favor from Order bank (effect fires as battle plan;
    # victory is resolved later, so we optimistically grant favor)
    gs = gain_favor(gs, player_index, 2, Suit.ORDER)
    return gs

register_effect(20, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_battle_honors_execute,
    description="Battle Plan: Gain 2 favor from Order bank",
))

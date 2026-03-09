"""Book Binders (OATH-140) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true, gain_favor, gain_favor_from_banks

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 141: Book Binders ─────────────────────────────────────────
# Modifier(Search): When Vision played, gain 2 favor from any bank.
def _book_binders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(141, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_book_binders_execute,
    description="Search: Gain 2 favor from any bank (when Vision played)",
))

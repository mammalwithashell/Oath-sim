"""Welcoming Party (OATH-050) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType, Suit
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 51: Welcoming Party ───────────────────────────────────────
# Modifier(Search): Gain 1 favor from Hearth bank when playing a card.
def _welcoming_party_execute(gs: 'GameState', player_index: int) -> 'GameState':
    hearth_idx = int(Suit.HEARTH)
    if gs.favor_banks[hearth_idx] > 0:
        gs.favor_banks[hearth_idx] -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(51, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_welcoming_party_execute,
    description="Search: Gain 1 favor from Hearth bank when playing a card",
))

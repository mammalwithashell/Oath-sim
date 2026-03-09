"""News from Afar (OATH-134) — Denizen (Hearth)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 135: News from Afar ───────────────────────────────────────
# Modifier(Search): Spend no supply (set _modifier_int = 0).
def _news_from_afar_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(135, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_news_from_afar_execute,
    description="Search: Spend no supply",
))

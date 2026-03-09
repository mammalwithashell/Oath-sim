"""True Names (OATH-041) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 45: True Names ────────────────────────────────────────────
# Modifier(Campaign): Enemy can't use battle plans matching your
# advisers. Simplified: +1 defense die.
def _true_names_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(45, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_true_names_execute,
    description="Campaign: Enemy can't use matching battle plans (+1 defense die)",
))

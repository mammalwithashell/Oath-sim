"""Marsh Spirit (OATH-192) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 193: Marsh Spirit ─────────────────────────────────────────
# Modifier(Campaign): Players targeting this site can't use battle
# plans. Simplified: +2 defense dice.
def _marsh_spirit_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(193, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_marsh_spirit_execute,
    description="Campaign: Enemies can't use battle plans at this site (+2 defense dice)",
))

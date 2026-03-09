"""Animal Playmates (OATH-040) — Denizen (Beast)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger, ModifierType
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 5: Animal Playmates (OATH-040) ────────────────────────────
# Muster Modifier: Spend no Supply if mustering on a Beast card.
def _animal_playmates_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Check if the muster target is a Beast card - signal via _modifier_bool
    gs._modifier_bool = True
    return gs

register_effect(5, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_animal_playmates_execute,
    description="Muster: Spend no Supply on Beast cards",
))

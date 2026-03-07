"""Card effect system for Oath simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING

from oath.enums import EffectTrigger

if TYPE_CHECKING:
    from oath.state.game_state import GameState


@dataclass
class CardEffect:
    """A single card effect definition."""
    trigger: EffectTrigger
    condition: Callable[['GameState', int], bool]
    execute: Callable[['GameState', int], 'GameState']
    cost_favor: int = 0
    cost_secrets: int = 0
    cost_burn_favor: int = 0
    cost_burn_secrets: int = 0
    requires_rule: bool = False
    description: str = ""


# Registry of card effects keyed by card_id
CARD_EFFECTS: dict[int, list[CardEffect]] = {}


def register_effect(card_id: int, effect: CardEffect) -> None:
    """Register an effect for a card."""
    if card_id not in CARD_EFFECTS:
        CARD_EFFECTS[card_id] = []
    CARD_EFFECTS[card_id].append(effect)


def get_effects(card_id: int) -> list[CardEffect]:
    """Get all effects for a card."""
    return CARD_EFFECTS.get(card_id, [])


def get_action_effects(card_id: int) -> list[CardEffect]:
    """Get ACTION trigger effects for a card."""
    return [e for e in get_effects(card_id) if e.trigger == EffectTrigger.ACTION]


def get_modifier_effects(card_id: int) -> list[CardEffect]:
    """Get MODIFIER trigger effects for a card."""
    return [e for e in get_effects(card_id) if e.trigger == EffectTrigger.MODIFIER]


def get_battle_plan_effects(card_id: int) -> list[CardEffect]:
    """Get BATTLE_PLAN trigger effects for a card."""
    return [e for e in get_effects(card_id) if e.trigger == EffectTrigger.BATTLE_PLAN]

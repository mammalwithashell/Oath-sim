"""Card effects package for Oath simulator."""

from oath.cards.effects._base import (
    CardEffect,
    CARD_EFFECTS,
    register_effect,
    get_effects,
    get_action_effects,
    get_modifier_effects,
    get_battle_plan_effects,
    get_when_played_effects,
    get_wake_effects,
    get_rest_effects,
    get_persistent_effects,
)

# Import all effect modules to trigger registration
from oath.cards.effects import order  # noqa: F401
from oath.cards.effects import arcane  # noqa: F401
from oath.cards.effects import hearth  # noqa: F401
from oath.cards.effects import beast  # noqa: F401
from oath.cards.effects import nomad  # noqa: F401
from oath.cards.effects import discord  # noqa: F401
from oath.cards.effects import relics  # noqa: F401
from oath.cards.effects import edifices  # noqa: F401

__all__ = [
    'CardEffect',
    'CARD_EFFECTS',
    'register_effect',
    'get_effects',
    'get_action_effects',
    'get_modifier_effects',
    'get_battle_plan_effects',
    'get_when_played_effects',
    'get_wake_effects',
    'get_rest_effects',
    'get_persistent_effects',
]

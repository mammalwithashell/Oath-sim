"""Edifice card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_supply, gain_secrets, gain_favor_from_banks,
)
from oath.enums import EffectTrigger, ModifierType, Suit

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 226: Great Hall (Sprawling Rampart, OATH-199) ─────────────
# Campaign Modifier: Each ruled site adds 1 more defense die when targeted
def _sprawling_rampart_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(226, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_sprawling_rampart_execute,
    description="Campaign: Each ruled site adds 1 defense die",
))


# ── ID 227: Ancient City (Fallen Spire, OATH-208) ───────────────
# Action: Swap cards from discard with Dispossessed (simplified: gain 1 favor)
def _fallen_spire_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(227, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_fallen_spire_execute,
    description="Action: Swap cards from discard",
))


# ── ID 228: Fallen Monastery (Squalid District, OATH-206) ───────
# Ruler may adjust game-end die roll (simplified: no-op)
register_effect(228, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Ruler may adjust end-game die roll",
))


# ── ID 229: Ruined Tower (Ruined Temple, OATH-204) ──────────────
# Enemies can't play Beast cards faceup (simplified: no-op)
register_effect(229, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Enemies can't play Beast cards faceup",
))


# ── ID 230: Broken Bridge (Ancient Forge, OATH-209) ─────────────
# Action: Draw a relic (simplified: gain 1 secret)
def _ancient_forge_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(230, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ancient_forge_execute,
    description="Action: Draw a relic",
))

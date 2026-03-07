"""Relic card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_warbands, gain_supply, gain_secrets,
    gain_favor_from_banks,
)
from oath.enums import EffectTrigger, ModifierType, Suit

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# Note: ID 19 (Sticky Fire, OATH-211) is already registered in arcane.py
# as it's in the first-game set

# ── ID 211: Grand Scepter (OATH-231) ─────────────────────────────
# Action: Peek in Reliquary / Offer Citizenship (simplified: gain 1 supply)
def _grand_scepter_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(211, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_grand_scepter_execute,
    description="Action: Peek at Reliquary or offer Citizenship",
))


# ── ID 212: Ivory Eye (OATH-226) ─────────────────────────────────
# Action: Peek at any facedown site/adviser/relic (no-op for RL)
def _ivory_eye_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(212, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ivory_eye_execute,
    description="Action: Peek at facedown card",
))


# ── ID 213: Cup of Plenty (OATH-217) ─────────────────────────────
# Trade Modifier: Spend no supply if trading with card matching advisers
def _cup_of_plenty_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(213, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_cup_of_plenty_execute,
    description="Trade: Spend no supply on cards matching advisers",
))


# ── ID 214: Book of Records (OATH-229) ───────────────────────────
# Persistent: Must gain secrets instead of favor when playing to site
# Simplified: no-op for RL
register_effect(214, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=lambda gs, pi: gs,
    description="Must gain secrets instead of favor when playing to site",
))


# ── ID 215: Skeleton Key (OATH-223) ──────────────────────────────
# Action: Peek at relic in Reliquary, may take it (simplified: gain 1 secret)
def _skeleton_key_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(215, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_skeleton_key_execute,
    description="Action: Peek at Reliquary relic",
))


# ── ID 216: Spirit Snare (OATH-216) ──────────────────────────────
# Relic: Horned Mask - Action: Swap faceup adviser with site card
# Simplified: gain 1 favor
def _spirit_snare_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(216, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_spirit_snare_execute,
    description="Action: Swap adviser with site card",
))


# ── ID 217: Relic 7 (Whistle, OATH-218) ──────────────────────────
# Action: Choose pawn at another site, they must travel to you
# Simplified: gain 1 supply
def _whistle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(217, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_whistle_execute,
    description="Action: Summon player to your site",
))


# ── ID 218: Relic 8 (Dowsing Sticks, OATH-219) ──────────────────
# Action: Draw a relic (simplified: gain 1 secret)
def _dowsing_sticks_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(218, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_dowsing_sticks_execute,
    description="Action: Draw a relic",
))


# ── ID 219: Relic 9 (Cursed Cauldron, OATH-212) ─────────────────
# Battle Plan: If victorious, gain 1 warband per enemy killed
# Simplified: +2 attack dice
def _cursed_cauldron_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is not None:
        if cs.campaign_attacker == player_index:
            cs.campaign_attack_dice += 2
        elif cs.campaign_defender == player_index:
            cs.campaign_defense_dice += 2
    return gs

register_effect(219, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_cursed_cauldron_execute,
    description="Battle Plan: Gain warbands per enemy killed",
))


# ── ID 220: Relic 10 (Brass Horse, OATH-213) ────────────────────
# Action: Travel for free based on discard pile top card
# Simplified: gain 2 supply
def _brass_horse_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(220, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_brass_horse_execute,
    description="Action: Free travel based on discard",
))

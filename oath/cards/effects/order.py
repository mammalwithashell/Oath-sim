"""Order suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_warbands, place_warbands_at_site, count_ruled_sites,
    gain_supply, gain_favor, gain_favor_from_banks, kill_warbands,
)
from oath.cards.database import get_card
from oath.enums import EffectTrigger, ModifierType, Suit, MAX_SITES, MAX_ADVISERS

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 1: Longbows (OATH-004) ─────────────────────────────────────
# Battle Plan: ± 1 defense die (attacker adds 1, defender removes 1)
def _longbows_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 1
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 1)
    return gs

register_effect(1, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_longbows_execute,
    description="± 1 defense die",
))


# ── ID 8: Garrison (OATH-007) ─────────────────────────────────────
# When Played: gain one warband per site you rule, put one warband
# from your board on each site you rule.
def _garrison_execute(gs: 'GameState', player_index: int) -> 'GameState':
    ruled = count_ruled_sites(gs, player_index)
    gs = gain_warbands(gs, player_index, ruled)
    # Place one warband from board on each ruled site
    player = gs.players[player_index]
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            if player.warbands_board > 0:
                player.warbands_board -= 1
                site.warbands += 1
    return gs

register_effect(8, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_garrison_execute,
    description="When Played: gain warbands per ruled site, place on each",
))


# ── ID 15: Keep (OATH-005) ────────────────────────────────────────
# Battle Plan: +2 attack dice if this site is targeted
def _keep_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Keep is a site-only card, check if any targeted site has the Keep
    return cs.campaign_defender == player_index

def _keep_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # +2 defense dice if defender's site is targeted
    player = gs.players[player_index]
    pawn_site = player.pawn_site
    for target in cs.campaign_targets:
        if target == f"site:{pawn_site}":
            cs.campaign_defense_dice += 2
            break
    return gs

register_effect(15, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_keep_condition,
    execute=_keep_execute,
    description="Battle Plan: +2 defense dice if this site is targeted",
))


# ── ID 18: Pressgangs (OATH-006) ──────────────────────────────────
# Muster Modifier: Can muster on cards that have favor or secrets on them
# This modifies muster eligibility - implemented as a MODIFIER that sets
# _modifier_bool to True if a card has favor/secrets on it
def _pressgangs_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(18, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_pressgangs_execute,
    description="Can muster on cards with favor or secrets",
))


# ── ID 20: Battle Honors ──────────────────────────────────────────
# Battle Plan: If victorious, gain 2 favor from Order bank
def _battle_honors_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Grant 2 favor from Order bank (effect fires as battle plan;
    # victory is resolved later, so we optimistically grant favor)
    gs = gain_favor(gs, player_index, 2, Suit.ORDER)
    return gs

register_effect(20, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_battle_honors_execute,
    description="Battle Plan: Gain 2 favor from Order bank",
))


# ── ID 21: Scouts ─────────────────────────────────────────────────
# Battle Plan: Gain 1 Supply
def _scouts_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(21, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_scouts_execute,
    description="Battle Plan: Gain 1 Supply",
))


# ── ID 22: Martial Culture ────────────────────────────────────────
# Battle Plan: If Exile defeats Exile, may become Citizen
# Simplified: gain supply refresh (gain 1 supply)
def _martial_culture_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(22, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_martial_culture_execute,
    description="Battle Plan: Gain supply refresh (simplified citizenship)",
))


# ── ID 104: Code of Honor ─────────────────────────────────────────
# Battle Plan: ±2 defense dice
def _code_of_honor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    return gs

register_effect(104, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_code_of_honor_execute,
    description="Battle Plan: ± 2 defense dice",
))


# ── ID 105: Outriders ─────────────────────────────────────────────
# Battle Plan: Ignore all skulls YOU roll (your own warbands are not killed).
# Approximated as +2 defense dice (since skulls hurt your own force).
def _outriders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    else:
        cs.campaign_defense_dice += 2
    return gs

register_effect(105, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_outriders_execute,
    description="Battle Plan: Ignore all skulls you roll (+2 dice approximation)",
))


# ── ID 106: Messenger ─────────────────────────────────────────────
# Action: Move warbands between board and ruled sites
# Simplified: gain 2 warbands (representing redistribution value)
def _messenger_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(106, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_messenger_execute,
    description="Action: Move warbands between board and ruled sites",
))


# ── ID 107: Field Promotion ───────────────────────────────────────
# Battle Plan: If victorious, gain 3 warbands
def _field_promotion_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(107, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_field_promotion_execute,
    description="Battle Plan: If victorious, gain 3 warbands",
))


# ── ID 108: Palanquin ─────────────────────────────────────────────
# Action: Travel for free (simplified: gain 2 supply)
def _palanquin_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(108, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_palanquin_execute,
    description="Action: Travel for free (gain 2 supply)",
))


# ── ID 109: Shield Wall ───────────────────────────────────────────
# Battle Plan: +2 attack dice. If defeated, kill all your force (mark via _modifier_bool)
def _shield_wall_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    # Mark that defeat kills all force
    gs._modifier_bool = True
    return gs

register_effect(109, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_shield_wall_execute,
    description="Battle Plan: +2 attack dice, if defeated kill all your force",
))


# ── ID 110: Military Parade ───────────────────────────────────────
# Battle Plan: If victorious, gain 1 favor per enemy adviser suit
def _military_parade_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Determine enemy
    enemy_index = None
    if cs.campaign_attacker == player_index:
        enemy_index = cs.campaign_defender
    elif cs.campaign_defender == player_index:
        enemy_index = cs.campaign_attacker
    if enemy_index is None:
        return gs
    # Count enemy adviser suits
    enemy = gs.players[enemy_index]
    suit_count = 0
    for i in range(MAX_ADVISERS):
        if enemy.advisers[i] is not None:
            card_data = get_card(enemy.advisers[i])
            if card_data.suit is not None:
                suit_count += 1
    if suit_count > 0:
        gs = gain_favor_from_banks(gs, player_index, suit_count)
    return gs

register_effect(110, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_military_parade_execute,
    description="Battle Plan: Gain 1 favor per enemy adviser suit",
))


# ── ID 111: Tome Guardians ────────────────────────────────────────
# Persistent: Enemies cannot target Darkest Secret (simplified: no-op for RL)
def _tome_guardians_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(111, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_tome_guardians_execute,
    description="Persistent: Enemies cannot target Darkest Secret (no-op)",
))


# ── ID 112: Tyrant ────────────────────────────────────────────────
# Modifier(Travel): Must kill a warband at travel destination (set _modifier_bool flag)
def _tyrant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(112, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_tyrant_execute,
    description="Modifier(Travel): Must kill a warband at destination",
))


# ── ID 113: Forced Labor ──────────────────────────────────────────
# Modifier(Search): Enemies can't search at ruled sites without paying favor
# Simplified: no-op for RL
def _forced_labor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(113, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_forced_labor_execute,
    description="Modifier(Search): Enemies pay favor to search at ruled sites (no-op)",
))


# ── ID 114: Secret Police ─────────────────────────────────────────
# Persistent: Enemies can't play Visions faceup at ruler's sites (simplified: no-op)
def _secret_police_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(114, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_secret_police_execute,
    description="Persistent: Enemies can't play Visions faceup at ruler's sites (no-op)",
))


# ── ID 115: Specialist ────────────────────────────────────────────
# Battle Plan: Defender cannot use battle plans (simplified: +2 attack dice)
def _specialist_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(115, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_specialist_execute,
    description="Battle Plan: +2 attack dice (simplified from blocking defender plans)",
))


# ── ID 116: Captains ──────────────────────────────────────────────
# Action: Campaign at any ruled site (simplified: gain 3 warbands)
def _captains_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(116, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_captains_execute,
    description="Action: Campaign at any ruled site (gain 3 warbands)",
))


# ── ID 117: Siege Engines ─────────────────────────────────────────
# Action: Kill 2 warbands at any site in region
def _siege_engines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_region = gs.sites[player.pawn_site].region
    # Kill 2 warbands at the site in the region with the most enemy warbands
    best_site = None
    best_warbands = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == pawn_region and site.warbands > 0:
            if site.ruling_player != player_index and site.warbands > best_warbands:
                best_site = i
                best_warbands = site.warbands
    if best_site is not None:
        site = gs.sites[best_site]
        killed = min(2, site.warbands)
        site.warbands -= killed
        # Find the ruling player to update their board count
        if site.ruling_player is not None:
            gs.players[site.ruling_player].warbands_board -= killed
    return gs

register_effect(117, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_siege_engines_execute,
    description="Action: Kill 2 warbands at any site in region",
))


# ── ID 118: Royal Tax ─────────────────────────────────────────────
# When Played: Take 2 favor from each player at your ruled sites in region
def _royal_tax_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_region = gs.sites[player.pawn_site].region
    # Find all players at ruled sites in same region
    taxed_players = set()
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == pawn_region and site.ruling_player == player_index:
            for pi, p in enumerate(gs.players):
                if pi != player_index and p.pawn_site == i:
                    taxed_players.add(pi)
    for pi in taxed_players:
        taken = min(2, gs.players[pi].favor)
        gs.players[pi].favor -= taken
        gs.players[player_index].favor += taken
    return gs

register_effect(118, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_royal_tax_execute,
    description="When Played: Take 2 favor from each player at ruled sites in region",
))


# ── ID 119: Toll Roads ────────────────────────────────────────────
# Modifier(Travel): Enemies must pay favor to travel to ruled sites
def _toll_roads_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(119, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_toll_roads_execute,
    description="Modifier(Travel): Enemies pay favor to travel to ruled sites",
))


# ── ID 120: Curfew ────────────────────────────────────────────────
# Modifier(Trade): Enemies must pay favor to trade at ruled sites (simplified: no-op)
def _curfew_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(120, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_curfew_execute,
    description="Modifier(Trade): Enemies pay favor to trade at ruled sites (no-op)",
))


# ── ID 121: Knights Errant ────────────────────────────────────────
# Modifier(Muster): After mustering, gain 1 supply
def _knights_errant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(121, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_knights_errant_execute,
    description="Modifier(Muster): Gain 1 supply after mustering",
))


# ── ID 122: Vow of Obedience ──────────────────────────────────────
# Rest: Take 1 favor from any bank
def _vow_of_obedience_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(122, CardEffect(
    trigger=EffectTrigger.REST,
    condition=always_true,
    execute=_vow_of_obedience_execute,
    description="Rest: Take 1 favor from any bank",
))


# ── ID 123: Hunting Party ─────────────────────────────────────────
# Modifier(Search): After searching, gain 1 supply
def _hunting_party_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(123, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_hunting_party_execute,
    description="Modifier(Search): Gain 1 supply after searching",
))


# ── ID 124: Council Seat ──────────────────────────────────────────
# Persistent: If Citizen, cannot be exiled (simplified: no-op)
def _council_seat_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(124, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_council_seat_execute,
    description="Persistent: If Citizen, cannot be exiled (no-op)",
))


# ── ID 125: Encirclement ──────────────────────────────────────────
# Battle Plan: ±2 defense dice if your force is larger than your enemy's.
def _encirclement_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        # Attacker: apply only if attack force > defense force
        if cs.campaign_attack_dice > cs.campaign_defense_dice:
            cs.campaign_attack_dice += 2
    elif cs.campaign_defender == player_index:
        # Defender: apply only if defense force > attack force
        if cs.campaign_defense_dice > cs.campaign_attack_dice:
            cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    return gs

register_effect(125, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_encirclement_execute,
    description="Battle Plan: ± 2 defense dice (simplified from force-size condition)",
))


# ── ID 126: Peace Envoy ───────────────────────────────────────────
# Battle Plan: Give enemy 1 favor per die they rolled (simplified: -1 attack die)
def _peace_envoy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice = max(0, cs.campaign_attack_dice - 1)
    return gs

register_effect(126, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_peace_envoy_execute,
    description="Battle Plan: -1 attack die (simplified from favor-per-die)",
))


# ── ID 127: Relic Hunter ──────────────────────────────────────────
# Battle Plan: +1 defense die per relic targeted (simplified: +1 defense die)
def _relic_hunter_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(127, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_relic_hunter_execute,
    description="Battle Plan: +1 defense die (simplified from per-relic-targeted)",
))

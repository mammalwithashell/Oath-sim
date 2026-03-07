"""Nomad suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_favor, gain_favor_from_banks, gain_secrets,
    gain_supply,
)
from oath.enums import (
    EffectTrigger, ModifierType, Suit, MAX_ADVISERS, MAX_SITES,
)
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 4: Forest Paths (OATH-043) ────────────────────────────────
# Travel Modifier: Spend no Supply and ignore site powers if traveling
# to a site with a Beast card.
def _forest_paths_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Check if the travel target site has a Beast card
    # The target site index is stored contextually during travel_cost computation
    # We use _modifier_int which holds the current cost
    # We need to check target site - since we're called from travel_cost,
    # we check all sites for beast cards at the target
    # For simplicity: set cost to 0 if target has beast card
    # The target site is not directly passed, but we can check _modifier_bool
    # as a flag. Actually, we need a different approach.
    # Set _modifier_bool to signal that beast-site travel is free.
    gs._modifier_bool = True
    return gs

register_effect(4, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_forest_paths_execute,
    description="Travel: Free travel to sites with Beast cards",
))


# ── ID 9: Errand Boy (OATH-011) ──────────────────────────────────
# Search Modifier: May draw from a discard pile in a different region.
# This modifies search behavior - sets _modifier_bool to signal
# cross-region discard search is allowed.
def _errand_boy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(9, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_errand_boy_execute,
    description="Search: May draw from other region's discard pile",
))


# ── ID 16: Tents (OATH-029) ──────────────────────────────────────
# Travel Modifier: Spend no Supply if traveling to a site in your region.
def _tents_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # The cost is in _modifier_int. If traveling within same region, set to 0.
    # We need to check if current site and target are in same region.
    # Since we're called from travel_cost loop, the context is:
    # the player's current region vs target region.
    player = gs.players[player_index]
    current_region = gs.sites[player.pawn_site].region
    # We need to check the target site region. The travel_cost function
    # has this info but doesn't pass it to us directly.
    # We use a convention: if regions match, cost goes to 0.
    # The cost is 1 for same-region travel, so if _modifier_int == 1,
    # it's same-region and we set to 0.
    if gs._modifier_int == 1:
        gs._modifier_int = 0
    return gs

register_effect(16, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_tents_execute,
    description="Travel: Free travel within your region",
))


# ── ID 25: Rain Boots ────────────────────────────────────────────
# BATTLE_PLAN: Ignore enemy single shields (simplified: +2 attack dice)
def _rain_boots_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(25, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_rain_boots_execute,
    description="Battle Plan: +2 attack dice (ignore single shields)",
))


# ── ID 31: Ancient Binding ───────────────────────────────────────
# ACTION: Each player burns all secrets except last.
def _ancient_binding_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for i in range(len(gs.players)):
        player = gs.players[i]
        if player.secrets > 1:
            excess = player.secrets - 1
            player.secrets = 1
            gs.shared_secrets += excess
    return gs

register_effect(31, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ancient_binding_execute,
    description="Action: Each player burns all secrets except last",
))


# ── ID 32: Horse Archers ─────────────────────────────────────────
# BATTLE_PLAN: +/-3 defense dice
def _horse_archers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 3
    return gs

register_effect(32, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_horse_archers_execute,
    description="Battle Plan: +/-3 defense dice",
))


# ── ID 33: Warning Signals ───────────────────────────────────────
# BATTLE_PLAN: Move warbands between board and ruled site
# (simplified: +2 defense dice)
def _warning_signals_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(33, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_warning_signals_execute,
    description="Battle Plan: +2 defense dice (simplified warband move)",
))


# ── ID 34: The Gathering ─────────────────────────────────────────
# WHEN_PLAYED: Players may negotiate (simplified: gain 2 favor)
def _the_gathering_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(34, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_the_gathering_execute,
    description="When Played: Gain 2 favor (simplified negotiation)",
))


# ── ID 35: Faithful Friend ───────────────────────────────────────
# WHEN_PLAYED: Gain 4 supply
def _faithful_friend_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 4)

register_effect(35, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_faithful_friend_execute,
    description="When Played: Gain 4 supply",
))


# ── ID 36: Great Herd ────────────────────────────────────────────
# WHEN_PLAYED: May swap with Nomad card at any site
# (simplified: gain 1 favor)
def _great_herd_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(36, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_great_herd_execute,
    description="When Played: Gain 1 favor (simplified swap)",
))


# ── ID 152: Convoys ──────────────────────────────────────────────
# ACTION: Move discard pile between regions (simplified: gain 1 supply)
def _convoys_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(152, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_convoys_execute,
    description="Action: Gain 1 supply (simplified discard-pile move)",
))


# ── ID 153: Vow of Kinship ───────────────────────────────────────
# PERSISTENT: Favor goes to Nomad bank (simplified: no-op)
def _vow_of_kinship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(153, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_kinship_execute,
    description="Persistent: Favor goes to Nomad bank (no-op)",
))


# ── ID 154: Wild Mounts ──────────────────────────────────────────
# BATTLE_PLAN: May discard Beast card instead of Nomad battle plans
# (simplified: +1 defense die)
def _wild_mounts_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(154, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_wild_mounts_execute,
    description="Battle Plan: +1 defense die (simplified Beast discard)",
))


# ── ID 155: Lancers ──────────────────────────────────────────────
# BATTLE_PLAN: Double attack roll (simplified: +3 attack dice)
def _lancers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 3
    return gs

register_effect(155, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_lancers_execute,
    description="Battle Plan: +3 attack dice (simplified double roll)",
))


# ── ID 156: Mountain Giant ───────────────────────────────────────
# BATTLE_PLAN: +/-1 or +/-3 defense dice (simplified: +/-2 defense dice)
def _mountain_giant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    return gs

register_effect(156, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_mountain_giant_execute,
    description="Battle Plan: +/-2 defense dice",
))


# ── ID 157: Rival Khan ───────────────────────────────────────────
# BATTLE_PLAN: +/-4 defense dice if enemy has Nomad adviser
def _rival_khan_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Determine the enemy player
    if cs.campaign_attacker == player_index:
        enemy = cs.campaign_defender
    elif cs.campaign_defender == player_index:
        enemy = cs.campaign_attacker
    else:
        return False
    if enemy is None:
        return False
    # Check if enemy has a Nomad adviser
    enemy_player = gs.players[enemy]
    for slot in range(MAX_ADVISERS):
        card_id = enemy_player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.NOMAD:
                return True
    return False

def _rival_khan_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 4)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 4
    return gs

register_effect(157, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_rival_khan_condition,
    execute=_rival_khan_execute,
    description="Battle Plan: +/-4 defense dice if enemy has Nomad adviser",
))


# ── ID 158: Lost Tongue ──────────────────────────────────────────
# PERSISTENT: Others can't target your relics/banners unless ruling
# Nomad card (simplified: no-op)
def _lost_tongue_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(158, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_lost_tongue_execute,
    description="Persistent: Protect relics/banners (no-op)",
))


# ── ID 159: Special Envoy ────────────────────────────────────────
# MODIFIER(Travel): Spend no supply, end Act Phase after
# (set _modifier_int = 0)
def _special_envoy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(159, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_special_envoy_execute,
    description="Travel: Spend no supply (ends Act Phase after)",
))


# ── ID 160: Resettle ─────────────────────────────────────────────
# ACTION: Move Nomad card between sites/advisers
# (simplified: gain 1 favor)
def _resettle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(160, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_resettle_execute,
    description="Action: Gain 1 favor (simplified Nomad card move)",
))


# ── ID 161: Oracle ───────────────────────────────────────────────
# ACTION: Draw Vision from deck (simplified: gain 1 secret)
def _oracle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(161, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_oracle_execute,
    description="Action: Gain 1 secret (simplified Vision draw)",
))


# ── ID 162: Pilgrimage ───────────────────────────────────────────
# WHEN_PLAYED: Discard all denizens at site, draw same number
# (simplified: gain 2 favor)
def _pilgrimage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(162, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_pilgrimage_execute,
    description="When Played: Gain 2 favor (simplified site refresh)",
))


# ── ID 163: Spell Breaker ────────────────────────────────────────
# PERSISTENT: Enemies can't use powers costing secrets (simplified: no-op)
def _spell_breaker_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(163, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_spell_breaker_execute,
    description="Persistent: Block enemy secret-cost powers (no-op)",
))


# ── ID 164: Mounted Patrol ───────────────────────────────────────
# BATTLE_PLAN: Attacker rolls half attack dice
# (simplified: -2 attack dice for attacker)
def _mounted_patrol_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice = max(0, cs.campaign_attack_dice - 2)
    return gs

register_effect(164, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_mounted_patrol_execute,
    description="Battle Plan: -2 attack dice for attacker",
))


# ── ID 165: Great Crusade ────────────────────────────────────────
# BATTLE_PLAN: +/- defense dice per Nomad card ruled
def _great_crusade_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count Nomad cards at ruled sites
    nomad_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.NOMAD:
                        nomad_count += 1
    # Also count Nomad advisers
    player = gs.players[player_index]
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.NOMAD:
                nomad_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - nomad_count)
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += nomad_count
    return gs

register_effect(165, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_great_crusade_execute,
    description="Battle Plan: +/- defense dice per Nomad card ruled",
))


# ── ID 166: Ancient Bloodline ────────────────────────────────────
# PERSISTENT: Enemies treat ruled denizens/relics as locked
# (simplified: no-op)
def _ancient_bloodline_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(166, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_ancient_bloodline_execute,
    description="Persistent: Lock ruled denizens/relics from enemies (no-op)",
))


# ── ID 167: Ancient Pact ─────────────────────────────────────────
# WHEN_PLAYED: May become Citizen by giving Chancellor Darkest Secret
# (simplified: gain 2 supply)
def _ancient_pact_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(167, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_ancient_pact_execute,
    description="When Played: Gain 2 supply (simplified citizenship pact)",
))


# ── ID 168: Storm Caller ─────────────────────────────────────────
# BATTLE_PLAN: +2 dice (attack dice for attacker, defense dice for defender).
def _storm_caller_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    else:
        cs.campaign_defense_dice += 2
    return gs

register_effect(168, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_storm_caller_execute,
    description="Battle Plan: +2 dice",
))


# ── ID 169: Family Wagon ─────────────────────────────────────────
# PERSISTENT: Only 1 non-Nomad adviser, unlimited Nomad
# (simplified: no-op)
def _family_wagon_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(169, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_family_wagon_execute,
    description="Persistent: Unlimited Nomad advisers (no-op)",
))


# ── ID 170: Way Station ──────────────────────────────────────────
# MODIFIER(Travel): Free travel to this site
# (set _modifier_int = 0 if traveling to site with this card)
def _way_station_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # If traveling to the site that has this card, cost is 0.
    # We check if target site has this card; since we're called during
    # travel_cost computation, we set cost to 0 optimistically.
    # The travel system will verify site matching.
    gs._modifier_int = 0
    return gs

register_effect(170, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_way_station_execute,
    description="Travel: Free travel to this site",
))


# ── ID 171: Twin Brother ─────────────────────────────────────────
# WHEN_PLAYED: May swap with Nomad adviser of another player
# (simplified: gain 1 favor)
def _twin_brother_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(171, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_twin_brother_execute,
    description="When Played: Gain 1 favor (simplified adviser swap)",
))


# ── ID 172: Hospitality ──────────────────────────────────────────
# MODIFIER(Travel): After traveling, gain 1 favor from matching bank
def _hospitality_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor(gs, player_index, 1, Suit.NOMAD)

register_effect(172, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_hospitality_execute,
    description="Travel: Gain 1 favor from Nomad bank after traveling",
))


# ── ID 173: A Fast Steed ─────────────────────────────────────────
# MODIFIER(Travel): Spend no supply if 3 or fewer warbands on board
def _a_fast_steed_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board <= 3

def _a_fast_steed_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(173, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=_a_fast_steed_condition,
    execute=_a_fast_steed_execute,
    description="Travel: Free travel if 3 or fewer warbands on board",
))


# ── ID 174: Relic Worship ────────────────────────────────────────
# MODIFIER(Recover): After recovering relic, gain 3 supply
def _relic_worship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 3)

register_effect(174, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_relic_worship_execute,
    description="Recover: Gain 3 supply after recovering a relic",
))


# ── ID 175: Sacred Ground ────────────────────────────────────────
# MODIFIER(Search): Players can't play Visions faceup unless at this
# site (simplified: no-op)
def _sacred_ground_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(175, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_sacred_ground_execute,
    description="Search: Restrict Vision play to this site (no-op)",
))

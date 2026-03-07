"""Discord suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_favor, gain_favor_from_banks, gain_secrets,
    gain_warbands, gain_supply,
)
from oath.enums import EffectTrigger, ModifierType, Role, Suit, MAX_ADVISERS, MAX_SITES
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 6: Naysayers (OATH-021) ───────────────────────────────────
# Rest: If any Exile is the Oathkeeper or Usurper, take favor from Chancellor.
def _naysayers_condition(gs: 'GameState', player_index: int) -> bool:
    # Check if any Exile holds the Oathkeeper title
    holder = gs.oathkeeper_holder
    if holder is not None and holder != gs.chancellor_index:
        if gs.players[holder].role in (Role.EXILE, Role.CITIZEN):
            return True
    return False

def _naysayers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    chancellor = gs.players[gs.chancellor_index]
    if chancellor.favor > 0:
        chancellor.favor -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(6, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_naysayers_condition,
    execute=_naysayers_execute,
    description="Rest: Take favor from Chancellor if Exile is Oathkeeper",
))


# ── ID 17: Wrestlers (OATH-001) ──────────────────────────────────
# Battle Plan: +1 attack die if you sacrifice one warband in your force.
def _wrestlers_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board > 0

def _wrestlers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    if player.warbands_board > 0:
        player.warbands_board -= 1
        site = gs.sites[player.pawn_site]
        if site.warbands > 0:
            site.warbands -= 1
        cs.campaign_attack_dice += 1
    return gs

register_effect(17, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_wrestlers_condition,
    execute=_wrestlers_execute,
    description="Battle Plan: Sacrifice 1 warband for +1 attack die",
))


# ── ID 23: Mercenaries ──────────────────────────────────────────
# Battle Plan: ±3 defense dice. If defeated, discard card.
def _mercenaries_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 3
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    return gs

register_effect(23, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_mercenaries_execute,
    description="Battle Plan: ±3 defense dice; if defeated, discard card",
))


# ── ID 26: Second Wind ──────────────────────────────────────────
# Battle Plan: If victorious, may travel+campaign free.
# Simplified: +2 attack dice.
def _second_wind_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(26, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_second_wind_execute,
    description="Battle Plan: +2 attack dice (simplified from travel+campaign if victorious)",
))


# ── ID 27: Sleight of Hand ──────────────────────────────────────
# Action: Take 1 secret from player at your site.
# Condition: another player at site with >1 secret.
def _sleight_of_hand_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for i in range(gs.num_players):
        if i != player_index and gs.players[i].pawn_site == player.pawn_site:
            if gs.players[i].secrets > 1:
                return True
    return False

def _sleight_of_hand_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Take 1 secret from the first eligible player at the same site
    for i in range(gs.num_players):
        if i != player_index and gs.players[i].pawn_site == player.pawn_site:
            if gs.players[i].secrets > 1:
                gs.players[i].secrets -= 1
                gs.players[player_index].secrets += 1
                break
    return gs

register_effect(27, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_sleight_of_hand_condition,
    execute=_sleight_of_hand_execute,
    description="Action: Take 1 secret from player at your site",
))


# ── ID 28: Key to the City ──────────────────────────────────────
# When Played: Kill warbands at site if ruler absent, gain+place warband.
# Simplified: gain 2 warbands.
def _key_to_the_city_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(28, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_key_to_the_city_execute,
    description="When Played: Gain 2 warbands (simplified)",
))


# ── ID 29: Disgraced Captain ────────────────────────────────────
# Battle Plan: +4 defense dice if targeting site with Order card.
def _disgraced_captain_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Check if any targeted site has an Order card
    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            site = gs.sites[site_idx]
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.ORDER:
                        return True
    return False

def _disgraced_captain_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 4
    return gs

register_effect(29, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_disgraced_captain_condition,
    execute=_disgraced_captain_execute,
    description="Battle Plan: +4 defense dice if targeting site with Order card",
))


# ── ID 30: Book Burning ─────────────────────────────────────────
# Battle Plan: If victorious and targeted pawn, burn enemy's secrets.
# Simplified: +2 attack dice.
def _book_burning_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(30, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_book_burning_execute,
    description="Battle Plan: +2 attack dice (simplified from burn enemy secrets if victorious)",
))


# ── ID 80: Charlatan ────────────────────────────────────────────
# When Played: Burn all but 1 secret from Darkest Secret.
# Simplified: gain 1 secret.
def _charlatan_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(80, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_charlatan_execute,
    description="When Played: Gain 1 secret (simplified)",
))


# ── ID 81: Assassin ─────────────────────────────────────────────
# Action: Discard faceup adviser of player at your site.
# Simplified: gain 1 favor.
def _assassin_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(81, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_assassin_execute,
    description="Action: Gain 1 favor (simplified from discard faceup adviser)",
))


# ── ID 82: Downtrodden ──────────────────────────────────────────
# Modifier(Muster): Gain 2 more warbands if mustering on card whose bank
# has least favor.
def _downtrodden_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Add 2 extra warbands via modifier int
    gs._modifier_int += 2
    return gs

register_effect(82, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_downtrodden_execute,
    description="Muster: Gain 2 more warbands if mustering on least-favor bank card",
))


# ── ID 83: Blackmail ────────────────────────────────────────────
# When Played: Take relic from player at site.
# Simplified: gain 2 favor.
def _blackmail_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(83, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_blackmail_execute,
    description="When Played: Gain 2 favor (simplified from take relic)",
))


# ── ID 84: Cracked Sage ─────────────────────────────────────────
# Battle Plan: ±4 defense dice if enemy has Arcane adviser.
def _cracked_sage_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    # Determine the enemy
    if cs.campaign_attacker == player_index:
        enemy = cs.campaign_defender
    elif cs.campaign_defender == player_index:
        enemy = cs.campaign_attacker
    else:
        return False
    if enemy is None:
        return False
    # Check if enemy has an Arcane adviser
    enemy_player = gs.players[enemy]
    for slot in range(MAX_ADVISERS):
        card_id = enemy_player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.ARCANE:
                return True
    return False

def _cracked_sage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 4
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 4)
    return gs

register_effect(84, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_cracked_sage_condition,
    execute=_cracked_sage_execute,
    description="Battle Plan: ±4 defense dice if enemy has Arcane adviser",
))


# ── ID 85: Dissent ──────────────────────────────────────────────
# When Played: Each player places favor on card per site ruled.
# Simplified: gain 2 favor.
def _dissent_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(85, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_dissent_execute,
    description="When Played: Gain 2 favor (simplified)",
))


# ── ID 86: False Prophet ────────────────────────────────────────
# When Played: If Exile, gain 1 warband.
# Simplified: gain 1 warband.
def _false_prophet_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 1)

register_effect(86, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_false_prophet_execute,
    description="When Played: Gain 1 warband (simplified)",
))


# ── ID 87: Vow of Renewal ───────────────────────────────────────
# Persistent: Can't recover People's Favor.
# Simplified: no-op.
def _vow_of_renewal_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(87, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_renewal_execute,
    description="Persistent: Can't recover People's Favor (no-op)",
))


# ── ID 88: Zealots ──────────────────────────────────────────────
# Battle Plan: If defending force larger, sacrificed warbands add 3 each.
# Simplified: +3 attack dice if defending force is larger.
def _zealots_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Only apply if defending force is larger than attacking force
    if cs.campaign_defense_dice > cs.campaign_attack_dice:
        cs.campaign_attack_dice += 3
    return gs

register_effect(88, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_zealots_execute,
    description="Battle Plan: +3 attack dice (simplified from sacrifice bonus)",
))


# ── ID 89: Royal Ambitions ──────────────────────────────────────
# When Played: If Exile ruling more sites than Chancellor, may become Citizen.
# Simplified: gain 2 supply.
def _royal_ambitions_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(89, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_royal_ambitions_execute,
    description="When Played: Gain 2 supply (simplified)",
))


# ── ID 90: Salt the Earth ───────────────────────────────────────
# When Played: Discard all cards at site.
# Simplified: gain 3 favor.
def _salt_the_earth_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 3)

register_effect(90, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_salt_the_earth_execute,
    description="When Played: Gain 3 favor (simplified from discard all cards at site)",
))


# ── ID 91: Beast Tamer ──────────────────────────────────────────
# Modifier(Campaign): Enemies can't use Beast/Nomad battle plans.
# Simplified: +1 defense die.
def _beast_tamer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(91, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_beast_tamer_execute,
    description="Campaign: +1 defense die (simplified from block Beast/Nomad battle plans)",
))


# ── ID 92: Riots ────────────────────────────────────────────────
# When Played: If People's Favor on Mob side, discard common suit.
# Simplified: gain 2 warbands.
def _riots_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(92, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_riots_execute,
    description="When Played: Gain 2 warbands (simplified)",
))


# ── ID 93: Silver Tongue ────────────────────────────────────────
# Rest: Take 1 favor from bank matching card at site.
def _silver_tongue_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit is not None:
                bank_idx = int(card_data.suit)
                if gs.favor_banks[bank_idx] > 0:
                    return True
    return False

def _silver_tongue_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    # Take 1 favor from the first matching bank with available favor
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit is not None:
                bank_idx = int(card_data.suit)
                if gs.favor_banks[bank_idx] > 0:
                    gs.favor_banks[bank_idx] -= 1
                    gs.players[player_index].favor += 1
                    break
    return gs

register_effect(93, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_silver_tongue_condition,
    execute=_silver_tongue_execute,
    description="Rest: Take 1 favor from bank matching card at site",
))


# ── ID 94: Gambling Hall ────────────────────────────────────────
# Action: Roll dice, gain favor equal to shields rolled.
# Simplified: gain 2 favor.
def _gambling_hall_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(94, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_gambling_hall_execute,
    description="Action: Gain 2 favor (simplified from dice roll)",
))


# ── ID 95: Boiling Lake ─────────────────────────────────────────
# Modifier(Travel): If traveling to site and don't rule, must kill 2 warbands.
# Set _modifier_bool to signal travel penalty.
def _boiling_lake_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(95, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_boiling_lake_execute,
    description="Travel: Must kill 2 warbands if traveling to site you don't rule",
))


# ── ID 96: Relic Thief ──────────────────────────────────────────
# Persistent: After player takes relics in your region, may steal.
# Simplified: no-op.
def _relic_thief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(96, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_relic_thief_execute,
    description="Persistent: May steal relics taken in your region (no-op)",
))


# ── ID 97: Enchantress ──────────────────────────────────────────
# Action: Swap this card with any faceup adviser.
# Simplified: gain 1 favor.
def _enchantress_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(97, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_enchantress_execute,
    description="Action: Gain 1 favor (simplified from swap adviser)",
))


# ── ID 98: Insomnia ─────────────────────────────────────────────
# Rest: Gain 1 secret.
def _insomnia_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(98, CardEffect(
    trigger=EffectTrigger.REST,
    condition=always_true,
    execute=_insomnia_execute,
    description="Rest: Gain 1 secret",
))


# ── ID 99: Sneak Attack ─────────────────────────────────────────
# Modifier(Campaign): After another player's campaign, may campaign free.
# Simplified: gain 1 supply.
def _sneak_attack_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 1)

register_effect(99, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_sneak_attack_execute,
    description="Campaign: Gain 1 supply (simplified from free campaign after enemy campaign)",
))


# ── ID 100: Gossip ──────────────────────────────────────────────
# Persistent: Enemies can't play cards as facedown advisers.
# Simplified: no-op.
def _gossip_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(100, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_gossip_execute,
    description="Persistent: Enemies can't play facedown advisers (no-op)",
))


# ── ID 101: Bandit Chief ────────────────────────────────────────
# When Played: Kill 1 warband at each site.
def _bandit_chief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.warbands > 0:
            site.warbands -= 1
    return gs

register_effect(101, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_bandit_chief_execute,
    description="When Played: Kill 1 warband at each site",
))


# ── ID 102: Chaos Cult ──────────────────────────────────────────
# Persistent: After player takes Oathkeeper, take favor from them.
# Simplified: no-op.
def _chaos_cult_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(102, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_chaos_cult_execute,
    description="Persistent: Take favor from new Oathkeeper (no-op)",
))


# ── ID 103: Slander ─────────────────────────────────────────────
# Battle Plan: If victorious and targeted pawn, burn all enemy favor.
# Simplified: +3 attack dice.
def _slander_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 3
    return gs

register_effect(103, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_slander_execute,
    description="Battle Plan: +3 attack dice (simplified from burn enemy favor if victorious)",
))

"""Beast suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_favor, gain_favor_from_banks, gain_secrets,
    gain_warbands, gain_supply, kill_warbands,
    count_ruled_sites,
)
from oath.enums import (
    EffectTrigger, ModifierType, Suit, Role,
    MAX_ADVISERS, MAX_SITES,
)
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 2: Taming Charm (OATH-037) ────────────────────────────────
# Action: Discard a Beast or Nomad card at your site to gain 2 favor
# from the matching favor bank.
def _taming_charm_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit in (Suit.BEAST, Suit.NOMAD):
                return True
    return False

def _taming_charm_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]
    # Discard first Beast or Nomad card found
    for slot in range(site.capacity):
        card_id = site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit in (Suit.BEAST, Suit.NOMAD):
                site.cards[slot] = None
                gs.discard_piles[int(site.region)].append(card_id)
                gs = gain_favor(gs, player_index, 2, card_data.suit)
                break
    return gs

register_effect(2, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_taming_charm_condition,
    execute=_taming_charm_execute,
    description="Action: Discard Beast/Nomad card at site for 2 favor",
))


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


# ── ID 10: The Old Oak (OATH-042) ────────────────────────────────
# Trade Modifier: If trading for secrets, gain one more secret if
# you have any Beast advisers.
def _old_oak_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                return True
    return False

def _old_oak_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(10, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=_old_oak_condition,
    execute=_old_oak_execute,
    description="Trade: +1 secret if you have Beast advisers",
))


# ── ID 13: Bear Traps (OATH-003) ─────────────────────────────────
# Battle Plan: -1 defense die. Kill one warband on attacker's board.
def _bear_traps_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Defender uses this: remove 1 attacker defense die, kill 1 attacker warband
    if cs.campaign_attacker is not None:
        attacker = gs.players[cs.campaign_attacker]
        if attacker.warbands_board > 0:
            attacker.warbands_board -= 1
            # Also reduce warbands at the attacker's site
            attacker_site = gs.sites[attacker.pawn_site]
            if attacker_site.warbands > 0:
                attacker_site.warbands -= 1
    return gs

register_effect(13, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_bear_traps_execute,
    description="Battle Plan: Kill 1 attacker warband",
))


# ── ID 44: Wolves ────────────────────────────────────────────────
# Action: Kill 1 warband on any board.
def _wolves_condition(gs: 'GameState', player_index: int) -> bool:
    # Check if any other player has warbands on their board
    for i, p in enumerate(gs.players):
        if i != player_index and p.warbands_board > 0:
            return True
    return False

def _wolves_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Kill 1 warband from the first opponent who has warbands
    for i, p in enumerate(gs.players):
        if i != player_index and p.warbands_board > 0:
            p.warbands_board -= 1
            break
    return gs

register_effect(44, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_wolves_condition,
    execute=_wolves_execute,
    description="Action: Kill 1 warband on any board",
))


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


# ── ID 46: Long-Lost Heir ────────────────────────────────────────
# When Played: If Exile, may become Citizen. Simplified: gain 3 supply.
def _long_lost_heir_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 3)

register_effect(46, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_long_lost_heir_execute,
    description="When Played: Gain 3 supply (simplified become Citizen)",
))


# ── ID 47: Rangers ───────────────────────────────────────────────
# Battle Plan: Ignore skulls, +2 defense dice if defense pool has 4+.
def _rangers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defense_dice >= 4:
        cs.campaign_defense_dice += 2
    return gs

register_effect(47, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_rangers_execute,
    description="Battle Plan: Ignore skulls, +2 defense dice if pool >= 4",
))


# ── ID 48: Roving Terror ─────────────────────────────────────────
# Action: Discard a denizen at any site. Simplified: gain 1 favor.
def _roving_terror_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(48, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_roving_terror_execute,
    description="Action: Discard denizen at any site (gain 1 favor)",
))


# ── ID 176: Nature Worship ───────────────────────────────────────
# Battle Plan: ±1 defense die per Beast adviser.
def _nature_worship_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    beast_count = 0
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                beast_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += beast_count
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += beast_count
    return gs

register_effect(176, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_nature_worship_execute,
    description="Battle Plan: ±1 defense die per Beast adviser",
))


# ── ID 177: Birdsong ─────────────────────────────────────────────
# Modifier(Trade): Spend no supply if trading with Beast or Nomad card.
def _birdsong_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(177, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_birdsong_execute,
    description="Trade: Spend no supply if trading with Beast/Nomad card",
))


# ── ID 178: Small Friends ────────────────────────────────────────
# Modifier(Trade): Act as if pawn at any site with Beast card.
# Simplified: no-op.
def _small_friends_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(178, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_small_friends_execute,
    description="Trade: Act as if pawn at site with Beast card (no-op)",
))


# ── ID 179: Grasping Vines ───────────────────────────────────────
# Modifier(Travel): Enemies traveling from ruled site must kill 1
# warband. Sets _modifier_bool.
def _grasping_vines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(179, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_grasping_vines_execute,
    description="Travel: Enemies leaving ruled site must kill 1 warband",
))


# ── ID 180: Threatening Roar ─────────────────────────────────────
# When Played: Discard all Nomad and Beast cards at sites in region.
# Simplified: gain 2 warbands.
def _threatening_roar_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 2)

register_effect(180, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_threatening_roar_execute,
    description="When Played: Gain 2 warbands (simplified discard Nomad/Beast)",
))


# ── ID 181: Fae Merchant ─────────────────────────────────────────
# Action: Draw a relic and take it. Simplified: gain 1 secret.
def _fae_merchant_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(181, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_fae_merchant_execute,
    description="Action: Draw and take relic (gain 1 secret)",
))


# ── ID 182: Second Chance ────────────────────────────────────────
# Action: Kill 1 warband on board of player with Order/Discord adviser.
# Simplified: gain 1 favor.
def _second_chance_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(182, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_second_chance_execute,
    description="Action: Kill warband on Order/Discord adviser holder (gain 1 favor)",
))


# ── ID 183: Pied Piper ───────────────────────────────────────────
# Action: Move card to another player's advisers, take 2 favor from
# them. Simplified: gain 2 favor.
def _pied_piper_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(183, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_pied_piper_execute,
    description="Action: Move card to other player's advisers (gain 2 favor)",
))


# ── ID 184: Mushrooms ────────────────────────────────────────────
# Modifier(Search): Spend no supply but draw only 1 card.
# Sets _modifier_int = 0.
def _mushrooms_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(184, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_mushrooms_execute,
    description="Search: Spend no supply, draw only 1 card",
))


# ── ID 185: Insect Swarm ─────────────────────────────────────────
# Modifier(Campaign): Enemy battle plans cost extra favor.
# Simplified: +1 defense die.
def _insect_swarm_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(185, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_insect_swarm_execute,
    description="Campaign: Enemy battle plans cost extra favor (+1 defense die)",
))


# ── ID 186: Vow of Union ─────────────────────────────────────────
# Persistent: Warbands at ruled sites add to attacking force.
# Simplified: no-op.
def _vow_of_union_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(186, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_vow_of_union_execute,
    description="Persistent: Warbands at ruled sites add to attack (no-op)",
))


# ── ID 187: Giant Python ─────────────────────────────────────────
# Modifier(Campaign): Enemy must declare targets with even defense.
# Simplified: +1 defense die.
def _giant_python_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 1
    return gs

register_effect(187, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_giant_python_execute,
    description="Campaign: Enemy targets must have even defense (+1 defense die)",
))


# ── ID 188: War Tortoise ─────────────────────────────────────────
# Battle Plan: Ignore double results from enemy. Simplified: +2
# defense dice.
def _war_tortoise_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(188, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_war_tortoise_execute,
    description="Battle Plan: Ignore enemy doubles (+2 defense dice)",
))


# ── ID 189: New Growth ───────────────────────────────────────────
# Modifier(Search): May play Beast/Hearth cards to any site.
# Simplified: set _modifier_bool.
def _new_growth_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(189, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_new_growth_execute,
    description="Search: May play Beast/Hearth cards to any site",
))


# ── ID 190: Wild Cry ─────────────────────────────────────────────
# Modifier(Search): If playing Beast card, gain 1 supply and 2 warbands.
def _wild_cry_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_supply(gs, player_index, 1)
    gs = gain_warbands(gs, player_index, 2)
    return gs

register_effect(190, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_wild_cry_execute,
    description="Search: If playing Beast card, gain 1 supply and 2 warbands",
))


# ── ID 191: Animal Host ──────────────────────────────────────────
# When Played: Gain warbands equal to Beast cards at sites in region.
def _animal_host_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    region = gs.sites[player.pawn_site].region
    beast_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.is_faceup and site.region == region:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.BEAST:
                        beast_count += 1
    return gain_warbands(gs, player_index, beast_count)

register_effect(191, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_animal_host_execute,
    description="When Played: Gain warbands equal to Beast cards in region",
))


# ── ID 192: Memory of Nature ─────────────────────────────────────
# Action: Move favor to Beast bank equal to Beast cards ruled.
def _memory_of_nature_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    if player.favor <= 0:
        return False
    # Check if player rules any site with Beast cards
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.BEAST:
                        return True
    return False

def _memory_of_nature_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    beast_count = 0
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.BEAST:
                        beast_count += 1
    # Move favor from player to Beast bank
    actual = min(beast_count, player.favor)
    player.favor -= actual
    gs.favor_banks[int(Suit.BEAST)] += actual
    return gs

register_effect(192, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_memory_of_nature_condition,
    execute=_memory_of_nature_execute,
    description="Action: Move favor to Beast bank equal to Beast cards ruled",
))


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


# ── ID 194: Vow of Poverty ───────────────────────────────────────
# Rest: If you have no favor, gain 2 favor from any bank.
def _vow_of_poverty_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].favor == 0

def _vow_of_poverty_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(194, CardEffect(
    trigger=EffectTrigger.REST,
    condition=_vow_of_poverty_condition,
    execute=_vow_of_poverty_execute,
    description="Rest: If no favor, gain 2 favor from any bank",
))


# ── ID 195: Forest Council ───────────────────────────────────────
# Persistent: Enemies can't trade with Beast cards. Simplified: no-op.
def _forest_council_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(195, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_forest_council_execute,
    description="Persistent: Enemies can't trade with Beast cards (no-op)",
))


# ── ID 196: Walled Garden ────────────────────────────────────────
# Battle Plan: ± defense dice per Beast card at sites if targeted.
def _walled_garden_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    player = gs.players[player_index]
    pawn_site = gs.sites[player.pawn_site]
    beast_count = 0
    for slot in range(pawn_site.capacity):
        card_id = pawn_site.cards[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.BEAST:
                beast_count += 1
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += beast_count
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += beast_count
    return gs

register_effect(196, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_walled_garden_execute,
    description="Battle Plan: ± defense dice per Beast card at site",
))


# ── ID 197: Vow of Beastkin ──────────────────────────────────────
# Modifier(Muster): Must muster on matching adviser card, gain 1
# more warband. Simplified: gain 1 extra warband.
def _vow_of_beastkin_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_warbands(gs, player_index, 1)
    return gs

register_effect(197, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_vow_of_beastkin_execute,
    description="Muster: Gain 1 extra warband",
))


# ── ID 198: Bracken ──────────────────────────────────────────────
# Modifier(Search): Put discards on top/bottom of any discard pile.
# Simplified: no-op.
def _bracken_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(198, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_bracken_execute,
    description="Search: Rearrange discard pile (no-op)",
))


# ── ID 199: Wild Allies ──────────────────────────────────────────
# Action: Campaign at site with Beast card. Simplified: gain 3 warbands.
def _wild_allies_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(199, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wild_allies_execute,
    description="Action: Campaign at Beast card site (gain 3 warbands)",
))

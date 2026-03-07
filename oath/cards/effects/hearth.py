"""Hearth suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_warbands, gain_supply, gain_favor, gain_favor_from_banks,
    gain_secrets,
)
from oath.enums import EffectTrigger, ModifierType, Suit, MAX_ADVISERS, MAX_SITES
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 3: Elders (OATH-026) ──────────────────────────────────────
# Action: Gain 1 favor.
def _elders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Gain 1 favor from any bank (take from largest)
    best_bank = max(range(len(gs.favor_banks)), key=lambda i: gs.favor_banks[i])
    if gs.favor_banks[best_bank] > 0:
        gs.favor_banks[best_bank] -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(3, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_elders_execute,
    description="Action: Gain 1 favor",
))


# ── ID 7: A Small Favor (OATH-015) ───────────────────────────────
# When Played: Gain four warbands.
def _a_small_favor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 4)

register_effect(7, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_a_small_favor_execute,
    description="When Played: Gain 4 warbands",
))


# ── ID 14: Wayside Inn (OATH-047) ────────────────────────────────
# Action: Gain 2 Supply.
def _wayside_inn_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(14, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wayside_inn_execute,
    description="Action: Gain 2 Supply",
))


# ── ID 24: Tinker's Fair ─────────────────────────────────────────
# Action: Negotiate exchange (simplified: gain 2 favor).
def _tinkers_fair_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(24, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_tinkers_fair_execute,
    description="Action: Gain 2 favor (negotiate exchange)",
))


# ── ID 49: Extra Provisions ──────────────────────────────────────
# Battle Plan: +2 attack dice.
def _extra_provisions_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_attack_dice += 2
    return gs

register_effect(49, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_extra_provisions_execute,
    description="Battle Plan: +2 attack dice",
))


# ── ID 50: Memory of Home ────────────────────────────────────────
# Action: Move all favor from one bank to Hearth bank.
def _memory_of_home_execute(gs: 'GameState', player_index: int) -> 'GameState':
    hearth_idx = int(Suit.HEARTH)
    # Find the largest non-Hearth bank and move all its favor to Hearth
    best_bank = -1
    best_amount = 0
    for i in range(len(gs.favor_banks)):
        if i != hearth_idx and gs.favor_banks[i] > best_amount:
            best_amount = gs.favor_banks[i]
            best_bank = i
    if best_bank >= 0 and best_amount > 0:
        gs.favor_banks[hearth_idx] += best_amount
        gs.favor_banks[best_bank] = 0
    return gs

register_effect(50, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_memory_of_home_execute,
    description="Action: Move all favor from one bank to Hearth bank",
))


# ── ID 51: Welcoming Party ───────────────────────────────────────
# Modifier(Search): Gain 1 favor from Hearth bank when playing a card.
def _welcoming_party_execute(gs: 'GameState', player_index: int) -> 'GameState':
    hearth_idx = int(Suit.HEARTH)
    if gs.favor_banks[hearth_idx] > 0:
        gs.favor_banks[hearth_idx] -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(51, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_welcoming_party_execute,
    description="Search: Gain 1 favor from Hearth bank when playing a card",
))


# ── ID 52: Traveling Doctor ──────────────────────────────────────
# Battle Plan: If defeated, kill no warbands (simplified: +2 defense dice).
def _traveling_doctor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 2
    return gs

register_effect(52, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_traveling_doctor_execute,
    description="Battle Plan: +2 defense dice (no warbands killed if defeated)",
))


# ── ID 53: Storyteller ───────────────────────────────────────────
# Action: Place 1 secret from shared bank on Darkest Secret
# (simplified: gain 1 secret).
def _storyteller_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(53, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_storyteller_execute,
    description="Action: Gain 1 secret (place on Darkest Secret)",
))


# ── ID 54: Armed Mob ─────────────────────────────────────────────
# Action: Discard a faceup adviser from Darkest Secret holder
# (simplified: gain 1 favor).
def _armed_mob_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(54, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_armed_mob_execute,
    description="Action: Gain 1 favor (discard adviser from DS holder)",
))


# ── ID 55: Tavern Songs ──────────────────────────────────────────
# Action: Peek at discard pile (no-op for RL).
def _tavern_songs_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # No-op for RL: discard piles are already observable.
    return gs

register_effect(55, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_tavern_songs_execute,
    description="Action: Peek at discard pile (no-op for RL)",
))


# ── ID 128: Homesteaders ─────────────────────────────────────────
# Action: Move adviser to site (simplified: gain 1 favor).
def _homesteaders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(128, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_homesteaders_execute,
    description="Action: Gain 1 favor (move adviser to site)",
))


# ── ID 129: Crop Rotation ────────────────────────────────────────
# Modifier(Search): May discard denizen at site before playing
# (simplified: no-op).
def _crop_rotation_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op for RL.
    return gs

register_effect(129, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_crop_rotation_execute,
    description="Search: May discard denizen at site before playing (no-op)",
))


# ── ID 130: A Round of Ale ───────────────────────────────────────
# Action: Return favor/secrets as in Rest (simplified: gain 2 supply).
def _a_round_of_ale_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_supply(gs, player_index, 2)

register_effect(130, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_a_round_of_ale_execute,
    description="Action: Gain 2 Supply (return favor/secrets as in Rest)",
))


# ── ID 131: Land Warden ──────────────────────────────────────────
# Modifier(Search): May play 2 cards (simplified: set _modifier_bool).
def _land_warden_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(131, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_land_warden_execute,
    description="Search: May play 2 cards",
))


# ── ID 132: Charming Friend ──────────────────────────────────────
# Action: Take 1 favor from player at your site.
def _charming_friend_condition(gs: 'GameState', player_index: int) -> bool:
    player = gs.players[player_index]
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site and p.favor > 0:
            return True
    return False

def _charming_friend_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Take 1 favor from the first other player at the same site who has favor
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site and p.favor > 0:
            p.favor -= 1
            player.favor += 1
            break
    return gs

register_effect(132, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_charming_friend_condition,
    execute=_charming_friend_execute,
    description="Action: Take 1 favor from player at your site",
))


# ── ID 133: Village Constable ────────────────────────────────────
# Battle Plan: ±2 defense dice.
def _village_constable_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    elif cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 2)
    return gs

register_effect(133, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_village_constable_execute,
    description="Battle Plan: ±2 defense dice",
))


# ── ID 134: Family Heirloom ──────────────────────────────────────
# When Played: Draw a relic (simplified: gain 1 secret).
def _family_heirloom_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(134, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_family_heirloom_execute,
    description="When Played: Gain 1 secret (draw a relic)",
))


# ── ID 135: News from Afar ───────────────────────────────────────
# Modifier(Search): Spend no supply (set _modifier_int = 0).
def _news_from_afar_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(135, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_news_from_afar_execute,
    description="Search: Spend no supply",
))


# ── ID 136: Levelers ─────────────────────────────────────────────
# Action: Move 2 favor from largest bank to smallest.
def _levelers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    banks = gs.favor_banks
    largest_idx = max(range(len(banks)), key=lambda i: banks[i])
    smallest_idx = min(range(len(banks)), key=lambda i: banks[i])
    if largest_idx != smallest_idx and banks[largest_idx] > 0:
        transfer = min(2, banks[largest_idx])
        banks[largest_idx] -= transfer
        banks[smallest_idx] += transfer
    return gs

register_effect(136, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_levelers_execute,
    description="Action: Move 2 favor from largest bank to smallest",
))


# ── ID 137: Fabled Feast ─────────────────────────────────────────
# When Played: Gain favor equal to Hearth cards you rule.
def _fabled_feast_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    hearth_count = 0
    # Count Hearth advisers
    for slot in range(MAX_ADVISERS):
        card_id = player.advisers[slot]
        if card_id is not None:
            card_data = get_card(card_id)
            if card_data.suit == Suit.HEARTH:
                hearth_count += 1
    # Count Hearth cards at ruled sites
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    card_data = get_card(card_id)
                    if card_data.suit == Suit.HEARTH:
                        hearth_count += 1
    if hearth_count > 0:
        gs = gain_favor_from_banks(gs, player_index, hearth_count)
    return gs

register_effect(137, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_fabled_feast_execute,
    description="When Played: Gain favor equal to Hearth cards you rule",
))


# ── ID 138: The Great Levy ───────────────────────────────────────
# Battle Plan: ±3 defense dice, ignore skulls.
def _the_great_levy_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 3
    elif cs.campaign_attacker == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    return gs

register_effect(138, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_the_great_levy_execute,
    description="Battle Plan: ±3 defense dice, ignore skulls",
))


# ── ID 139: Hearts and Minds ─────────────────────────────────────
# Battle Plan: As defender, instant victory (simplified: +5 defense dice).
def _hearts_and_minds_condition(gs: 'GameState', player_index: int) -> bool:
    cs = gs.compound_state
    if cs is None:
        return False
    return cs.campaign_defender == player_index

def _hearts_and_minds_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 5
    return gs

register_effect(139, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_hearts_and_minds_condition,
    execute=_hearts_and_minds_execute,
    description="Battle Plan: +5 defense dice (instant victory as defender)",
))


# ── ID 140: Relic Breaker ────────────────────────────────────────
# Action: Put relic on bottom of deck, gain 3 warbands
# (simplified: gain 3 warbands).
def _relic_breaker_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_warbands(gs, player_index, 3)

register_effect(140, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_relic_breaker_execute,
    description="Action: Gain 3 warbands (break a relic)",
))


# ── ID 141: Book Binders ─────────────────────────────────────────
# Modifier(Search): When Vision played, gain 2 favor
# (simplified: gain 1 favor from Hearth bank).
def _book_binders_execute(gs: 'GameState', player_index: int) -> 'GameState':
    hearth_idx = int(Suit.HEARTH)
    if gs.favor_banks[hearth_idx] > 0:
        gs.favor_banks[hearth_idx] -= 1
        gs.players[player_index].favor += 1
    return gs

register_effect(141, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_book_binders_execute,
    description="Search: Gain 1 favor from Hearth bank (when Vision played)",
))


# ── ID 142: Ballot Box ───────────────────────────────────────────
# Action: If Exile with People's Favor, become Citizen
# (simplified: gain 2 favor).
def _ballot_box_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(142, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ballot_box_execute,
    description="Action: Gain 2 favor (become Citizen if Exile with People's Favor)",
))


# ── ID 143: Saddle Makers ────────────────────────────────────────
# Modifier(Search): When Nomad/Order played, gain 2 favor
# (simplified: gain 1 favor).
def _saddle_makers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(143, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_saddle_makers_execute,
    description="Search: Gain 1 favor when Nomad/Order card played",
))


# ── ID 144: Herald ───────────────────────────────────────────────
# Modifier(Campaign): After another player campaigns, gain 1 favor.
def _herald_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(144, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_herald_execute,
    description="Campaign: Gain 1 favor after another player campaigns",
))


# ── ID 145: Rowdy Pub ────────────────────────────────────────────
# Modifier(Muster): Gain 1 more warband when mustering from this card.
def _rowdy_pub_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(145, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_rowdy_pub_execute,
    description="Muster: Gain 1 more warband when mustering from this card",
))


# ── ID 146: Vow of Peace ─────────────────────────────────────────
# Modifier(Campaign): Cannot campaign (simplified: no-op for RL).
def _vow_of_peace_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op for RL.
    return gs

register_effect(146, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_vow_of_peace_execute,
    description="Campaign: Cannot campaign (no-op for RL)",
))


# ── ID 147: Deed Writer ──────────────────────────────────────────
# Action: Exchange sites (simplified: gain 2 favor).
def _deed_writer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 2)

register_effect(147, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_deed_writer_execute,
    description="Action: Gain 2 favor (exchange sites)",
))


# ── ID 148: Salad Days ───────────────────────────────────────────
# When Played: Gain 3 favor from 3 different banks.
def _salad_days_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Take 1 favor from each of the 3 largest banks
    banks = gs.favor_banks
    # Get bank indices sorted by amount descending
    sorted_banks = sorted(range(len(banks)), key=lambda i: banks[i], reverse=True)
    taken = 0
    for bank_idx in sorted_banks:
        if taken >= 3:
            break
        if banks[bank_idx] > 0:
            banks[bank_idx] -= 1
            gs.players[player_index].favor += 1
            taken += 1
    return gs

register_effect(148, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_salad_days_execute,
    description="When Played: Gain 3 favor from 3 different banks",
))


# ── ID 149: Marriage ─────────────────────────────────────────────
# Persistent: Counts as 2 Hearth advisers (simplified: no-op).
def _marriage_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # Simplified: no-op. Counting logic handled elsewhere.
    return gs

register_effect(149, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_marriage_execute,
    description="Persistent: Counts as 2 Hearth advisers (no-op)",
))


# ── ID 150: Hospital ─────────────────────────────────────────────
# Battle Plan: Warbands placed on site instead of killed
# (simplified: +3 defense dice).
def _hospital_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    cs.campaign_defense_dice += 3
    return gs

register_effect(150, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_hospital_execute,
    description="Battle Plan: +3 defense dice (warbands saved to site)",
))


# ── ID 151: Awaited Return ───────────────────────────────────────
# Modifier(Trade): Spend no supply if sacrifice 1 warband.
def _awaited_return_condition(gs: 'GameState', player_index: int) -> bool:
    return gs.players[player_index].warbands_board > 0

def _awaited_return_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    if player.warbands_board > 0:
        player.warbands_board -= 1
        # Signal free trade
        gs._modifier_int = 0
    return gs

register_effect(151, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=_awaited_return_condition,
    execute=_awaited_return_execute,
    description="Trade: Spend no supply if sacrifice 1 warband",
))

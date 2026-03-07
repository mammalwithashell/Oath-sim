"""Arcane suit card effects for Oath simulator."""

from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.cards.effects._helpers import (
    always_true, gain_favor, gain_favor_from_banks, gain_secrets,
    has_min_secrets, count_ruled_sites,
)
from oath.enums import EffectTrigger, ModifierType, Suit, MAX_SITES

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── Condition helpers (local) ────────────────────────────────────

def _has_darkest_secret(gs: 'GameState', player_index: int) -> bool:
    """Check if player holds the Darkest Secret."""
    return gs.darkest_secret_holder == player_index


def _has_warbands_on_board(min_count: int):
    """Return a condition checking player has at least min_count warbands on board."""
    def _check(gs: 'GameState', player_index: int) -> bool:
        return gs.players[player_index].warbands_board >= min_count
    return _check


def _has_secrets_and_player_at_site(gs: 'GameState', player_index: int) -> bool:
    """Check if player has secrets and another player is at the same site."""
    player = gs.players[player_index]
    if player.secrets < 1:
        return False
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site:
            return True
    return False


# ── ID 11: Alchemist (OATH-009) ───────────────────────────────────
# Action: Gain 4 favor from any favor bank or banks.
def _alchemist_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 4)

register_effect(11, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_alchemist_execute,
    description="Action: Gain 4 favor from any banks",
))


# ── ID 12: Scryer (OATH-019) ─────────────────────────────────────
# Action: Peek at any one discard pile.
# In the RL simulator, this is largely a no-op since info is encoded
# in observations. We implement it as a free action that reveals
# discard pile info (no state change needed for RL purposes).
def _scryer_execute(gs: 'GameState', player_index: int) -> 'GameState':
    # In a full implementation, this would reveal hidden information.
    # For the RL simulator, discard piles are already observable.
    return gs

register_effect(12, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_scryer_execute,
    description="Action: Peek at any discard pile",
))


# ── ID 19: Sticky Fire (OATH-211) ────────────────────────────────
# Battle Plan: If victorious, kill all warbands in enemy's force.
# Must give them favor if able.
def _sticky_fire_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Mark that sticky fire is active - will be resolved in campaign victory
    # For now, we set _modifier_bool as a flag
    gs._modifier_bool = True
    return gs

register_effect(19, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_sticky_fire_execute,
    description="Battle Plan: If victorious, kill all enemy warbands, give them favor",
))


# ── ID 37: Fire Talkers ──────────────────────────────────────────
# Battle Plan: +/- 3 defense dice if holding Darkest Secret.
def _fire_talkers_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 3
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - 3)
    return gs

register_effect(37, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_has_darkest_secret,
    execute=_fire_talkers_execute,
    description="Battle Plan: +/- 3 defense dice if holding Darkest Secret",
))


# ── ID 38: Magician's Code ───────────────────────────────────────
# Modifier(Recover): If recovering Darkest Secret, gain 2 secrets.
# Simplified: gain 2 secrets when condition met.
def _magicians_code_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs = gain_secrets(gs, player_index, 2)
    return gs

register_effect(38, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_magicians_code_execute,
    description="Recover: Gain 2 secrets when recovering Darkest Secret",
))


# ── ID 39: Spirit Snare ──────────────────────────────────────────
# Action: Take 1 favor from any bank.
def _spirit_snare_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor_from_banks(gs, player_index, 1)

register_effect(39, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_spirit_snare_execute,
    description="Action: Take 1 favor from any bank",
))


# ── ID 40: Wizard School ─────────────────────────────────────────
# Action: Gain 1 secret, then end Act Phase.
# Simplified: gain 1 secret.
def _wizard_school_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(40, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_wizard_school_execute,
    description="Action: Gain 1 secret (ends Act Phase)",
))


# ── ID 41: Dazzle ────────────────────────────────────────────────
# When Played: Discard all Hearth and Order cards at sites in region.
# Simplified: gain 2 favor.
def _dazzle_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_favor(gs, player_index, 2)

register_effect(41, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_dazzle_execute,
    description="When Played: Gain 2 favor (simplified from discard Hearth/Order)",
))


# ── ID 42: Acting Troupe ─────────────────────────────────────────
# Modifier(Trade): Act as if card is Beast or Order.
# Simplified: set _modifier_bool.
def _acting_troupe_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(42, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_acting_troupe_execute,
    description="Trade: Act as if card is Beast or Order",
))


# ── ID 43: Inquisitor ────────────────────────────────────────────
# Action: Peek at adviser of player at your site.
# Simplified: gain 1 secret.
def _inquisitor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(43, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_inquisitor_execute,
    description="Action: Gain 1 secret (simplified from peek at adviser)",
))


# ── ID 56: Secret Signal ─────────────────────────────────────────
# Modifier(Trade): If gain only 1 favor, gain 1 more.
# Simplified: set _modifier_int += 1.
def _secret_signal_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(56, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_secret_signal_execute,
    description="Trade: +1 favor if gaining only 1",
))


# ── ID 57: Augury ────────────────────────────────────────────────
# Modifier(Search): Draw 1 more card.
# Simplified: set _modifier_int += 1.
def _augury_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int += 1
    return gs

register_effect(57, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_augury_execute,
    description="Search: Draw 1 more card",
))


# ── ID 58: Rusting Ray ───────────────────────────────────────────
# Battle Plan: If holding Darkest Secret, ignore hollow swords.
# Simplified: +2 attack dice if holding DS.
def _rusting_ray_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 2
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 2
    return gs

register_effect(58, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=_has_darkest_secret,
    execute=_rusting_ray_execute,
    description="Battle Plan: +2 attack dice if holding Darkest Secret",
))


# ── ID 59: Portal ────────────────────────────────────────────────
# Modifier(Travel): Free travel to/from this site.
# Simplified: set _modifier_int = 0.
def _portal_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_int = 0
    return gs

register_effect(59, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRAVEL,
    condition=always_true,
    execute=_portal_execute,
    description="Travel: Free travel to/from this site",
))


# ── ID 60: Billowing Fog ─────────────────────────────────────────
# Battle Plan: If defeated, kill no warbands.
# Simplified: +3 defense dice.
def _billowing_fog_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 3
    elif cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += 3
    return gs

register_effect(60, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_billowing_fog_execute,
    description="Battle Plan: +3 defense dice (simplified from no kills if defeated)",
))


# ── ID 61: Kindred Warriors ──────────────────────────────────────
# Battle Plan: Ignore skulls, +/- defense dice per other suit ruled.
def _kindred_warriors_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count distinct suits ruled by this player (excluding Arcane)
    ruled_suits = set()
    for i in range(MAX_SITES):
        site = gs.sites[i]
        if site.ruling_player == player_index and site.is_faceup:
            # Count each unique suit of cards at ruled sites
            for slot in range(site.capacity):
                card_id = site.cards[slot]
                if card_id is not None:
                    from oath.cards.database import get_card
                    card_data = get_card(card_id)
                    if card_data.suit != Suit.ARCANE:
                        ruled_suits.add(card_data.suit)
    bonus = len(ruled_suits)
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += bonus
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - bonus)
    return gs

register_effect(61, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_kindred_warriors_execute,
    description="Battle Plan: Ignore skulls, +/- defense dice per other suit ruled",
))


# ── ID 62: Terror Spells ─────────────────────────────────────────
# Action: Kill 2 warbands in region if holding Darkest Secret.
def _terror_spells_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    pawn_site = gs.sites[player.pawn_site]
    region = pawn_site.region
    kills_remaining = 2
    for i in range(MAX_SITES):
        if kills_remaining <= 0:
            break
        site = gs.sites[i]
        if site.region == region and site.is_faceup:
            # Kill warbands belonging to other players at this site
            for pi in range(len(gs.players)):
                if pi == player_index or kills_remaining <= 0:
                    continue
                # Simplified: reduce site warbands and player board warbands
                kill = min(kills_remaining, site.warbands)
                if kill > 0:
                    site.warbands -= kill
                    gs.players[pi].warbands_board -= min(kill, gs.players[pi].warbands_board)
                    kills_remaining -= kill
    return gs

register_effect(62, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_has_darkest_secret,
    execute=_terror_spells_execute,
    description="Action: Kill 2 warbands in region (requires Darkest Secret)",
))


# ── ID 63: Blood Pact ────────────────────────────────────────────
# Action: Sacrifice 2 warbands on board, gain 1 secret.
def _blood_pact_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    player.warbands_board -= 2
    return gain_secrets(gs, player_index, 1)

register_effect(63, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_has_warbands_on_board(2),
    execute=_blood_pact_execute,
    description="Action: Sacrifice 2 warbands, gain 1 secret",
))


# ── ID 64: Revelation ────────────────────────────────────────────
# When Played: Players may burn favor to gain secrets.
# Simplified: gain 1 secret.
def _revelation_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(64, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_revelation_execute,
    description="When Played: Gain 1 secret (simplified from burn favor for secrets)",
))


# ── ID 65: Observatory ───────────────────────────────────────────
# Modifier(Search): May draw from any discard pile.
# Simplified: set _modifier_bool.
def _observatory_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(65, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.SEARCH,
    condition=always_true,
    execute=_observatory_execute,
    description="Search: May draw from any discard pile",
))


# ── ID 66: Plague Engines ────────────────────────────────────────
# Action: Each player places 1 favor per site ruled into Arcane bank.
def _plague_engines_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for pi in range(len(gs.players)):
        ruled = count_ruled_sites(gs, pi)
        if ruled > 0:
            player = gs.players[pi]
            transfer = min(ruled, player.favor)
            player.favor -= transfer
            gs.favor_banks[int(Suit.ARCANE)] += transfer
    return gs

register_effect(66, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_plague_engines_execute,
    description="Action: Each player places 1 favor per ruled site into Arcane bank",
))


# ── ID 67: Gleaming Armor ────────────────────────────────────────
# Modifier(Campaign): Enemy battle plans cost extra secret.
# Simplified: +1 defense die.
def _gleaming_armor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 1
    return gs

register_effect(67, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_gleaming_armor_execute,
    description="Campaign: +1 defense die (simplified from extra battle plan cost)",
))


# ── ID 68: Bewitch ───────────────────────────────────────────────
# When Played: If Exile with more secrets than Chancellor, may become Citizen.
# Simplified: gain 2 secrets.
def _bewitch_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 2)

register_effect(68, CardEffect(
    trigger=EffectTrigger.WHEN_PLAYED,
    condition=always_true,
    execute=_bewitch_execute,
    description="When Played: Gain 2 secrets (simplified from citizenship swap)",
))


# ── ID 69: Jinx ──────────────────────────────────────────────────
# Persistent: May reroll dice.
# Simplified: no-op.
def _jinx_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(69, CardEffect(
    trigger=EffectTrigger.PERSISTENT,
    condition=always_true,
    execute=_jinx_execute,
    description="Persistent: May reroll dice (no-op in simulator)",
))


# ── ID 70: Tutor ─────────────────────────────────────────────────
# Action: Gain 1 secret.
def _tutor_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(70, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_tutor_execute,
    description="Action: Gain 1 secret",
))


# ── ID 71: Dream Thief ───────────────────────────────────────────
# Action: Swap 2 facedown advisers.
# Simplified: gain 1 secret.
def _dream_thief_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(71, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_dream_thief_execute,
    description="Action: Gain 1 secret (simplified from swap advisers)",
))


# ── ID 72: Cracking Ground ───────────────────────────────────────
# Battle Plan: +/- defense dice per site targeted.
def _cracking_ground_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count number of targeted sites
    site_targets = sum(1 for t in cs.campaign_targets if t.startswith("site:"))
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += site_targets
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - site_targets)
    return gs

register_effect(72, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_cracking_ground_execute,
    description="Battle Plan: +/- defense dice per site targeted",
))


# ── ID 73: Sealing Ward ──────────────────────────────────────────
# Modifier(Campaign): Relics add 1 more defense die when targeted.
# Simplified: +1 defense die.
def _sealing_ward_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    if cs.campaign_defender == player_index:
        cs.campaign_defense_dice += 1
    return gs

register_effect(73, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.CAMPAIGN,
    condition=always_true,
    execute=_sealing_ward_execute,
    description="Campaign: +1 defense die (simplified from relic defense bonus)",
))


# ── ID 74: Initiation Rite ───────────────────────────────────────
# Modifier(Muster): Must place secrets instead of favor to muster.
# Simplified: set _modifier_bool.
def _initiation_rite_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(74, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.MUSTER,
    condition=always_true,
    execute=_initiation_rite_execute,
    description="Muster: Must place secrets instead of favor",
))


# ── ID 75: Vow of Silence ────────────────────────────────────────
# Modifier(Recover): Can't recover Darkest Secret.
# Simplified: no-op.
def _vow_of_silence_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gs

register_effect(75, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.RECOVER,
    condition=always_true,
    execute=_vow_of_silence_execute,
    description="Recover: Can't recover Darkest Secret (no-op in simulator)",
))


# ── ID 76: Forgotten Vault ───────────────────────────────────────
# Action: Place secret on Darkest Secret or burn secret from it.
# Simplified: gain 1 secret.
def _forgotten_vault_execute(gs: 'GameState', player_index: int) -> 'GameState':
    return gain_secrets(gs, player_index, 1)

register_effect(76, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_forgotten_vault_execute,
    description="Action: Gain 1 secret (simplified from DS token manipulation)",
))


# ── ID 77: Map Library ───────────────────────────────────────────
# Modifier(Trade): May trade with card at any site in region.
# Simplified: set _modifier_bool.
def _map_library_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(77, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_map_library_execute,
    description="Trade: May trade with card at any site in region",
))


# ── ID 78: Witch's Bargain ───────────────────────────────────────
# Action: Give secret to player at site, take 2 favor.
def _witchs_bargain_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    # Give 1 secret to another player at the same site
    for pi in range(len(gs.players)):
        if pi != player_index and gs.players[pi].pawn_site == player.pawn_site:
            player.secrets -= 1
            gs.players[pi].secrets += 1
            break
    # Take 2 favor from that player (simplified: just gain 2 favor)
    player.favor += 2
    return gs

register_effect(78, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=_has_secrets_and_player_at_site,
    execute=_witchs_bargain_execute,
    description="Action: Give 1 secret to player at site, take 2 favor",
))


# ── ID 79: Master of Disguise ────────────────────────────────────
# Modifier(Trade): Act as if you had another player's advisers.
# Simplified: set _modifier_bool.
def _master_of_disguise_execute(gs: 'GameState', player_index: int) -> 'GameState':
    gs._modifier_bool = True
    return gs

register_effect(79, CardEffect(
    trigger=EffectTrigger.MODIFIER,
    modifier_type=ModifierType.TRADE,
    condition=always_true,
    execute=_master_of_disguise_execute,
    description="Trade: Act as if you had another player's advisers",
))

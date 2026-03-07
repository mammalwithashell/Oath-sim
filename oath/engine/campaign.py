"""Campaign resolution for Oath simulator.

Handles dice rolling, sacrifice mechanics, target declaration,
and campaign outcome resolution.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.enums import (
    ActionType, CompoundStateType, Phase, Role, Region, TitleSide,
    MAX_ADVISERS,
)
from oath.state.game_state import GameState, CompoundState, ActionRecord
from oath.cards.database import get_card
from oath.cards.effects import get_battle_plan_effects


# Oath attack die faces: 0=miss, 1=hit, 2=double-hit, S=skull(kills 2 warbands)
# Simplified: each die has faces [0, 0, 1, 1, 1, S]
# We represent skull as -1
ATTACK_DIE = [0, 0, 1, 1, 1, -1]
# Defense die faces: [0, 0, 1, 1, 2, 2]
DEFENSE_DIE = [0, 0, 1, 1, 2, 2]


def can_campaign(gs: GameState, player_index: int, target_player: int) -> bool:
    """Check if player can declare a campaign against a target."""
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 1:
        return False

    if target_player == player_index:
        return False

    if target_player < 0 or target_player >= gs.num_players:
        return False

    # Must be at same site or target rules a site in same region
    target = gs.players[target_player]
    player_site = gs.sites[player.pawn_site]

    # Check if at same site
    if player.pawn_site == target.pawn_site:
        return True

    # Check if target rules any site in same region
    for site in gs.sites:
        if site.ruling_player == target_player and site.region == player_site.region:
            return True

    return False


def execute_campaign_declare(gs: GameState, player_index: int, target_player: int) -> GameState:
    """Declare a campaign against a target player."""
    if not can_campaign(gs, player_index, target_player):
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError(f"Cannot campaign against player {target_player}")

    player = gs.players[player_index]
    player.supply -= 1
    gs.supply_spent_this_turn += 1

    gs.compound_state = CompoundState(
        state_type=CompoundStateType.CAMPAIGN_TARGETS,
        campaign_attacker=player_index,
        campaign_defender=target_player,
    )

    from oath.engine.actions import _record_action
    _record_action(gs, player_index, ActionType.CAMPAIGN_DECLARE,
                   target_player=target_player)
    return gs


def execute_campaign_target_site(gs: GameState, player_index: int, site_index: int) -> GameState:
    """Add a site as a campaign target."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_TARGETS:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign target state")

    cs.campaign_target_sites.append(site_index)
    cs.campaign_targets.append(f"site:{site_index}")
    return gs


def execute_campaign_target_relic(gs: GameState, player_index: int, relic_slot: int) -> GameState:
    """Add a relic as a campaign target."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_TARGETS:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign target state")

    cs.campaign_targets.append(f"relic:{relic_slot}")
    return gs


def execute_campaign_target_pawn(gs: GameState, player_index: int) -> GameState:
    """Target the defender's pawn (banishes them)."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_TARGETS:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign target state")

    cs.campaign_targets.append("pawn")
    return gs


def execute_campaign_done_targets(gs: GameState, player_index: int) -> GameState:
    """Finish declaring campaign targets, move to battle plan phase."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_TARGETS:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign target state")

    if not cs.campaign_targets:
        # Must have at least one target; default to site ruling
        defender = cs.campaign_defender
        if defender is not None:
            player = gs.players[player_index]
            site = gs.sites[player.pawn_site]
            if site.ruling_player == defender:
                cs.campaign_targets.append(f"site:{player.pawn_site}")

    cs.state_type = CompoundStateType.CAMPAIGN_BATTLE
    return gs


def execute_campaign_battle_plan(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Use a card's battle plan ability."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BATTLE:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign battle state")

    player = gs.players[player_index]
    if card_slot < MAX_ADVISERS:
        card_id = player.advisers[card_slot]
    else:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Invalid battle plan card slot")

    if card_id is not None:
        effects = get_battle_plan_effects(card_id)
        for effect in effects:
            if effect.condition(gs, player_index):
                gs = effect.execute(gs, player_index)
                break

    # Proceed to dice roll
    _resolve_campaign_dice(gs)
    return gs


def execute_campaign_no_battle(gs: GameState, player_index: int) -> GameState:
    """Decline to use a battle plan. Proceed to dice roll."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BATTLE:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign battle state")

    _resolve_campaign_dice(gs)
    return gs


def _resolve_campaign_dice(gs: GameState) -> None:
    """Roll campaign dice and determine if sacrifice is needed."""
    cs = gs.compound_state
    if cs is None:
        return

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None or defender is None:
        return

    attacker_player = gs.players[attacker]
    defender_player = gs.players[defender]

    # Count attacker dice: base = warbands at attacker's site belonging to attacker
    attacker_site = gs.sites[attacker_player.pawn_site]
    attack_dice = attacker_site.warbands if attacker_site.ruling_player == attacker else 0
    # Minimum 1 die for the pawn
    attack_dice = max(1, attack_dice)
    cs.campaign_attack_dice = attack_dice

    # Count defender dice: warbands at targeted sites
    defense_dice = 0
    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            site = gs.sites[site_idx]
            defense_dice += site.warbands
            # Add site defense value
            card_data = get_card(site.site_id)
            defense_dice += card_data.defense

    defense_dice = max(1, defense_dice)
    cs.campaign_defense_dice = defense_dice

    # Roll dice
    attack_total = 0
    skulls = 0
    for _ in range(attack_dice):
        roll = gs.rng.choice(ATTACK_DIE)
        if roll == -1:
            skulls += 1
        else:
            attack_total += roll

    defense_total = 0
    for _ in range(defense_dice):
        defense_total += gs.rng.choice(DEFENSE_DIE)

    # Skulls kill 2 attacker warbands each
    warband_losses = skulls * 2
    actual_losses = min(warband_losses, attacker_player.warbands_board)
    attacker_player.warbands_board -= actual_losses
    attacker_site.warbands = max(0, attacker_site.warbands - actual_losses)

    cs.campaign_attack_result = attack_total
    cs.campaign_defense_result = defense_total

    if attack_total >= defense_total:
        # Attack succeeds
        _resolve_campaign_victory(gs)
    else:
        # Check if sacrifice can close the gap
        deficit = defense_total - attack_total
        max_sacrifice = min(attacker_player.warbands_board, 5)
        if max_sacrifice >= deficit:
            cs.state_type = CompoundStateType.CAMPAIGN_SACRIFICE
        else:
            _resolve_campaign_defeat(gs)


def execute_campaign_sacrifice(gs: GameState, player_index: int, count: int) -> GameState:
    """Sacrifice warbands to boost attack."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_SACRIFICE:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign sacrifice state")

    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    actual_sacrifice = min(count, player.warbands_board)
    player.warbands_board -= actual_sacrifice
    site.warbands = max(0, site.warbands - actual_sacrifice)

    cs.campaign_attack_result += actual_sacrifice

    if cs.campaign_attack_result >= cs.campaign_defense_result:
        _resolve_campaign_victory(gs)
    else:
        _resolve_campaign_defeat(gs)

    return gs


def _resolve_campaign_victory(gs: GameState) -> None:
    """Resolve a successful campaign."""
    cs = gs.compound_state
    if cs is None:
        return

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None or defender is None:
        gs.compound_state = None
        return

    attacker_player = gs.players[attacker]
    defender_player = gs.players[defender]

    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            site = gs.sites[site_idx]
            # Remove defender warbands
            defender_player.warbands_board = max(0,
                defender_player.warbands_board - site.warbands)
            site.warbands = 0
            site.ruling_player = attacker

        elif target.startswith("relic:"):
            relic_slot = int(target.split(":")[1])
            if relic_slot < len(defender_player.relics):
                relic = defender_player.relics.pop(relic_slot)
                attacker_player.relics.append(relic)

        elif target == "pawn":
            # Banish defender: move to farthest site
            _banish_player(gs, defender)

    # Check if Oathkeeper title should flip
    if gs.oathkeeper_holder == defender:
        gs.oathkeeper_holder = attacker
        gs.oathkeeper_side = TitleSide.USURPER

    gs.compound_state = None


def _resolve_campaign_defeat(gs: GameState) -> None:
    """Resolve a failed campaign."""
    gs.compound_state = None


def _banish_player(gs: GameState, player_index: int) -> None:
    """Banish a player to the farthest site."""
    player = gs.players[player_index]
    current_region = gs.sites[player.pawn_site].region

    # Move to farthest region
    if current_region == Region.CRADLE:
        target_region = Region.HINTERLAND
    else:
        target_region = Region.CRADLE
    # Find first faceup site in target region
    for i, site in enumerate(gs.sites):
        if site.region == target_region and site.is_faceup:
            player.pawn_site = i
            break

    # Lose half of favor and secrets
    lost_favor = player.favor // 2
    lost_secrets = player.secrets // 2
    player.favor -= lost_favor
    player.secrets -= lost_secrets
    # Return to banks
    gs.shared_secrets += lost_secrets

"""Campaign resolution for Oath simulator.

Handles dice rolling, sacrifice mechanics, target declaration,
and campaign outcome resolution.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.enums import (
    ActionType, CompoundStateType, Phase, Role, TitleSide,
    OathGoal, MAX_ADVISERS,
)
from oath.state.game_state import GameState, CompoundState, ActionRecord
from oath.cards.database import get_card, SHROUDED_WOOD_ID
from oath.cards.effects import get_battle_plan_effects


# Oath attack die faces (§5.5.5): Sword ×3, Hollow Sword ×2, Skull ×1
# Two hollow swords pair into 1 sword; a lone hollow sword = 0.
# Each skull kills 1 attacker warband.
ATTACK_DIE = ['sword', 'sword', 'sword', 'hollow', 'hollow', 'skull']
# Defense die faces (§5.5.4): Blank ×2, Shield ×2, Double-Shield(⊗) ×1,
# Shield+Double(⊗) ×1.  The ⊗ marker DOUBLES total shields.
# Multiple ⊗ stack multiplicatively (×2, ×4, ×8...).
DEFENSE_DIE = ['blank', 'blank', 'shield', 'shield', 'double', 'shield_double']


def _count_attack_hits(rolls: list[str]) -> tuple[int, int]:
    """Count attack hits and skulls from rolled die faces.

    Returns (hits, skulls).
    Two hollow swords pair into 1 hit; a remaining lone hollow = 0.
    """
    swords = rolls.count('sword')
    hollows = rolls.count('hollow')
    skulls = rolls.count('skull')
    hits = swords + hollows // 2
    return hits, skulls


def _count_defense_shields(rolls: list[str]) -> int:
    """Count total defense shields from rolled die faces.

    'shield' = 1 base shield.
    'double' = 0 base shields + 1 doubler.
    'shield_double' = 1 base shield + 1 doubler.
    Total = base_shields × 2^doublers.
    """
    base_shields = 0
    doublers = 0
    for face in rolls:
        if face == 'shield':
            base_shields += 1
        elif face == 'double':
            doublers += 1
        elif face == 'shield_double':
            base_shields += 1
            doublers += 1
        # 'blank' contributes nothing
    return base_shields * (2 ** doublers) if base_shields > 0 else 0


def can_campaign_bandits(gs: GameState, player_index: int) -> bool:
    """Check if player can campaign against bandits at their site (§2.8.3, §5.5.1).

    Bandits can be targeted when no player rules the attacker's site.
    """
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 2:
        return False

    site = gs.sites[player.pawn_site]
    # Can target bandits only when no player rules this site
    return site.ruling_player is None and site.is_faceup


def can_campaign(gs: GameState, player_index: int, target_player: int) -> bool:
    """Check if player can declare a campaign against a target.

    target_player = -1 means bandits (no player defender).
    """
    if gs.phase != Phase.ACT or gs.in_compound_action:
        return False

    player = gs.players[player_index]
    if player.supply < 2:
        return False

    if target_player == player_index:
        return False

    # Bandits target (§2.8.3, §5.5.1)
    if target_player == -1:
        return can_campaign_bandits(gs, player_index)

    if target_player < 0 or target_player >= gs.num_players:
        return False

    # §5.5.1: Target must rule your site OR have their pawn at your site
    target = gs.players[target_player]
    player_site = gs.sites[player.pawn_site]

    # Check if target's pawn is at attacker's site
    if player.pawn_site == target.pawn_site:
        return True

    # Check if target rules the attacker's specific site
    if player_site.ruling_player == target_player:
        return True

    return False


def execute_campaign_declare(gs: GameState, player_index: int, target_player: int) -> GameState:
    """Declare a campaign against a target player."""
    if not can_campaign(gs, player_index, target_player):
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError(f"Cannot campaign against player {target_player}")

    player = gs.players[player_index]
    player.supply -= 2
    gs.supply_spent_this_turn += 2

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
        if defender is not None and defender >= 0:
            player = gs.players[player_index]
            site = gs.sites[player.pawn_site]
            if site.ruling_player == defender:
                cs.campaign_targets.append(f"site:{player.pawn_site}")
                cs.campaign_target_sites.append(player.pawn_site)
        elif defender == -1:
            # Bandits: target the attacker's site
            player = gs.players[player_index]
            cs.campaign_targets.append(f"site:{player.pawn_site}")
            cs.campaign_target_sites.append(player.pawn_site)

    cs.state_type = CompoundStateType.CAMPAIGN_BATTLE
    return gs


def execute_campaign_battle_plan(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Use a card's battle plan ability (attacker phase, §5.5.3)."""
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

    # §5.5.3: After attacker, move to defender battle plan phase
    # Bandits have no defender battle plan — skip straight to dice
    if cs.campaign_defender == -1:
        _resolve_campaign_dice(gs)
    else:
        cs.state_type = CompoundStateType.CAMPAIGN_BATTLE_DEFENDER
    return gs


def execute_campaign_no_battle(gs: GameState, player_index: int) -> GameState:
    """Decline to use a battle plan."""
    cs = gs.compound_state
    if cs is None:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign battle state")

    if cs.state_type == CompoundStateType.CAMPAIGN_BATTLE:
        # Attacker declined — move to defender battle plan phase
        # Bandits have no defender — skip straight to dice
        if cs.campaign_defender == -1:
            _resolve_campaign_dice(gs)
        else:
            cs.state_type = CompoundStateType.CAMPAIGN_BATTLE_DEFENDER
    elif cs.state_type == CompoundStateType.CAMPAIGN_BATTLE_DEFENDER:
        # Defender declined — proceed to dice roll
        _resolve_campaign_dice(gs)
    else:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign battle state")

    return gs


def execute_campaign_defender_battle_plan(gs: GameState, player_index: int, card_slot: int) -> GameState:
    """Use a card's battle plan ability (defender phase, §5.5.3)."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BATTLE_DEFENDER:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in defender battle plan state")

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

    # After defender battle plan, resolve dice
    _resolve_campaign_dice(gs)
    return gs


def _determine_imperial_allies(gs: GameState) -> list[int]:
    """Determine which Imperial players auto-join as allies (§5.5.3).

    Called when the defender is an Imperial player (Chancellor or Citizen).
    Returns a list of player indices who join as allies.

    Rules:
    - §5.5.1: If a Citizen is attacking another Imperial player, the
      attacker is NOT Imperial during this campaign.
    - §5.5.3: Chancellor always joins as ally (if not the defender/attacker).
    - §5.5.3: Citizens auto-join if their pawn is at the attacker's site
      or any targeted site (simplified heuristic for RL).
    """
    cs = gs.compound_state
    if cs is None:
        return []

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None or defender is None or defender < 0:
        return []

    # Defender must be Imperial
    if not gs.is_imperial(defender):
        return []

    attacker_player = gs.players[attacker]
    targeted_site_indices = list(cs.campaign_target_sites)

    allies = []
    for i in range(gs.num_players):
        if i == defender or i == attacker:
            continue
        player = gs.players[i]

        # §5.5.1: A Citizen attacking another Imperial is not Imperial
        # during this campaign — and by extension, other Citizens who are
        # the attacker are excluded above. But we also need to check: if
        # the attacker is a Citizen (attacking an Imperial), then other
        # Imperial players can still ally with the defender.

        # Only Imperial players can be allies
        if not gs.is_imperial(i):
            continue

        # Chancellor always joins as ally
        if player.role == Role.CHANCELLOR:
            allies.append(i)
            continue

        # Citizens join if their pawn is at the attacker's site or a targeted site
        if (player.pawn_site == attacker_player.pawn_site
                or player.pawn_site in targeted_site_indices):
            allies.append(i)

    return allies


def _resolve_campaign_dice(gs: GameState) -> None:
    """Roll campaign dice and determine if sacrifice is needed.

    Handles both player-vs-player and player-vs-bandits (defender == -1).
    """
    cs = gs.compound_state
    if cs is None:
        return

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None:
        return

    is_bandit_campaign = (defender == -1)

    attacker_player = gs.players[attacker]

    # Count attacker dice: warbands on attacker's board (§5.5.2)
    attacker_site = gs.sites[attacker_player.pawn_site]
    attack_dice = max(1, attacker_player.warbands_board)
    cs.campaign_attack_dice = attack_dice

    # §5.5.3: Determine Imperial allies before computing defense
    if not is_bandit_campaign and defender is not None and gs.is_imperial(defender):
        allies = _determine_imperial_allies(gs)
        cs.campaign_allies = allies
    else:
        cs.campaign_allies = []

    # Count defense dice (from site card defense values) and flat bonus (warbands)
    defense_dice = 0
    defense_flat = 0  # Flat bonus added after rolling
    targeted_site_indices = []
    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            targeted_site_indices.append(site_idx)
            site = gs.sites[site_idx]
            if not is_bandit_campaign:
                # Warbands at targeted sites are a flat bonus (§5.5.4)
                defense_flat += site.warbands
            # Site defense die value is rolled as dice (§2.8.3)
            # For bandits, site defense dice represent the bandit strength
            card_data = get_card(site.site_id)
            defense_dice += card_data.defense

    if not is_bandit_campaign and defender is not None:
        defender_player = gs.players[defender]

        # §5.5.4: Add defender's board warbands if their pawn is at the
        # attacker's site or at any targeted site
        defender_at_relevant_site = (
            defender_player.pawn_site == attacker_player.pawn_site
            or defender_player.pawn_site in targeted_site_indices
        )
        if defender_at_relevant_site:
            defense_flat += defender_player.warbands_board

        # §5.5.4: Add ally warbands to defense flat bonus.
        # Each ally whose pawn is at the attacker's site or a targeted site
        # contributes their warbands_board to the defense.
        for ally_idx in cs.campaign_allies:
            ally_player = gs.players[ally_idx]
            ally_at_relevant_site = (
                ally_player.pawn_site == attacker_player.pawn_site
                or ally_player.pawn_site in targeted_site_indices
            )
            if ally_at_relevant_site:
                defense_flat += ally_player.warbands_board

        # §5.5.3 (simplified): Each ally with battle plan cards gets +1
        # defense die (auto-resolved since RL can't model multi-player
        # compound state cycling for ally battle plan selection).
        for ally_idx in cs.campaign_allies:
            ally_player = gs.players[ally_idx]
            has_battle_plan = False
            for card_id in ally_player.advisers:
                if card_id is not None:
                    effects = get_battle_plan_effects(card_id)
                    if effects:
                        has_battle_plan = True
                        break
            if has_battle_plan:
                defense_dice += 1

        # Oathkeeper/Usurper defense dice (§2.11)
        if gs.oathkeeper_holder == defender:
            if gs.oathkeeper_side == TitleSide.OATHKEEPER:
                defense_dice += 1
            elif gs.oathkeeper_side == TitleSide.USURPER:
                defense_dice += 2

    defense_dice = max(1, defense_dice)
    cs.campaign_defense_dice = defense_dice

    # Roll attack dice using string-typed faces
    attack_rolls = [gs.rng.choice(ATTACK_DIE) for _ in range(attack_dice)]
    attack_total, skulls = _count_attack_hits(attack_rolls)

    # Roll defense dice using string-typed faces with doubler logic
    defense_rolls = [gs.rng.choice(DEFENSE_DIE) for _ in range(defense_dice)]
    defense_total = defense_flat + _count_defense_shields(defense_rolls)

    # Skulls kill 1 attacker warband each (§5.5.5)
    warband_losses = skulls
    actual_losses = min(warband_losses, attacker_player.warbands_board)
    attacker_player.warbands_board -= actual_losses
    attacker_site.warbands = max(0, attacker_site.warbands - actual_losses)
    if attacker_site.warbands <= 0 and attacker_site.ruling_player == attacker:
        attacker_site.ruling_player = None
        attacker_site.warband_color = None

    cs.campaign_attack_result = attack_total
    cs.campaign_defense_result = defense_total

    if attack_total > defense_total:
        # Attack succeeds (§5.5.5: attack must be strictly higher)
        _resolve_campaign_victory(gs)
    else:
        # Check if sacrifice can close the gap (need attack > defense)
        deficit = defense_total - attack_total
        max_sacrifice = min(attacker_player.warbands_board, 5)
        if max_sacrifice > deficit:
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
    if site.warbands <= 0 and site.ruling_player == player_index:
        site.ruling_player = None
        site.warband_color = None

    cs.campaign_attack_result += actual_sacrifice

    if cs.campaign_attack_result > cs.campaign_defense_result:
        _resolve_campaign_victory(gs)
    else:
        _resolve_campaign_defeat(gs)

    return gs


def _resolve_campaign_victory(gs: GameState) -> None:
    """Resolve a successful campaign (§5.5.7).

    Processes targets in rules order: I) sites, II) relics/banners, III) pawn.
    For site targets, removes defender warbands immediately, then enters
    CAMPAIGN_PLACE_WARBANDS state so the attacker can choose how many
    warbands (0 to force_remaining) to place on each targeted site.
    Relics/banners are transferred immediately. Pawn banishment enters
    banish compound states after warband placement is complete.
    """
    cs = gs.compound_state
    if cs is None:
        return

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None:
        gs.compound_state = None
        return

    is_bandit_campaign = (defender == -1)
    attacker_player = gs.players[attacker]
    defender_player = gs.players[defender] if not is_bandit_campaign and defender is not None else None

    has_pawn_target = False
    targeted_site_indices = []

    for target in cs.campaign_targets:
        if target.startswith("site:"):
            site_idx = int(target.split(":")[1])
            targeted_site_indices.append(site_idx)
            site = gs.sites[site_idx]

            if is_bandit_campaign:
                # Bandits: no warbands to remove, just clear site ruling
                site.warbands = 0
                site.ruling_player = None
                site.warband_color = None
            else:
                removed_warbands = site.warbands

                # §5.5.7.I: Imperial warbands at captured sites go to
                # Chancellor's board (bank). Non-imperial warbands are killed.
                if defender_player is not None and defender_player.role in (Role.CHANCELLOR, Role.CITIZEN):
                    chancellor = gs.players[gs.chancellor_index]
                    chancellor.warbands_bank += removed_warbands
                if defender_player is not None:
                    defender_player.warbands_board = max(0,
                        defender_player.warbands_board - removed_warbands)
                site.warbands = 0
                site.ruling_player = None
                site.warband_color = None

        elif target.startswith("relic:"):
            if not is_bandit_campaign and defender_player is not None:
                relic_slot = int(target.split(":")[1])
                if relic_slot < len(defender_player.relics):
                    relic = defender_player.relics.pop(relic_slot)
                    attacker_player.relics.append(relic)

        elif target == "pawn":
            if not is_bandit_campaign:
                has_pawn_target = True

    # §5.5.7.I: If there are targeted sites, enter warband placement state
    # so the attacker can choose how many warbands to place on each site.
    if targeted_site_indices:
        cs.campaign_remaining_sites = list(targeted_site_indices)
        cs.campaign_force_remaining = attacker_player.warbands_board
        cs.state_type = CompoundStateType.CAMPAIGN_PLACE_WARBANDS
        # Store whether pawn is targeted for after placement completes
        if has_pawn_target:
            cs.banish_target = defender
    else:
        # No site targets — skip to banish or finish
        if has_pawn_target:
            cs.state_type = CompoundStateType.CAMPAIGN_BANISH_TRAVEL
            cs.banish_target = defender
        else:
            recalculate_oathkeeper(gs)
            gs.compound_state = None


def execute_campaign_place_warbands(gs: GameState, player_index: int, count: int) -> GameState:
    """Place warbands on the current targeted site (§5.5.7.I).

    The attacker chooses how many warbands (0 to force_remaining) to place
    on each targeted site. After all sites have been assigned warbands,
    proceeds to banish phase (if pawn was targeted) or finishes the campaign.
    """
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_PLACE_WARBANDS:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in campaign place warbands state")

    if not cs.campaign_remaining_sites:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("No remaining sites for warband placement")

    attacker = cs.campaign_attacker
    if attacker is None:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("No campaign attacker")

    attacker_player = gs.players[attacker]

    # Clamp count to available force
    actual_count = min(count, cs.campaign_force_remaining)
    actual_count = max(0, actual_count)

    # Place warbands on the current site
    site_idx = cs.campaign_remaining_sites.pop(0)
    site = gs.sites[site_idx]
    site.warbands += actual_count
    if site.warbands > 0:
        site.ruling_player = attacker
        site.warband_color = 0 if gs.is_imperial(attacker) else attacker
    else:
        site.ruling_player = None
        site.warband_color = None

    # warbands_board represents total deployed warbands; placing on a captured
    # site doesn't change the total because the warbands are just relocated
    # from the attacker's "force" (board) to the site.
    # However, force_remaining tracks how many are left to distribute.
    cs.campaign_force_remaining -= actual_count

    if cs.campaign_remaining_sites:
        # More sites to place warbands on
        return gs

    # All sites done — proceed to banish or finish
    if cs.banish_target is not None:
        cs.state_type = CompoundStateType.CAMPAIGN_BANISH_TRAVEL
    else:
        recalculate_oathkeeper(gs)
        gs.compound_state = None

    return gs


def _resolve_campaign_defeat(gs: GameState) -> None:
    """Resolve a failed campaign (§5.5.6).

    The defeated player kills half (rounded down) of warbands in their force.
    - Attacker's force = warbands on their board (warbands_board).
    - Defender's force = warbands at targeted sites + warbands on board if
      their pawn was at the attacker's site or a targeted site.
    Killed warbands go to the defeated player's personal bank.
    When the defender loses, warbands are removed from targeted sites first,
    then from board if needed.

    For bandit campaigns (defender == -1): attacker always loses (bandits cannot
    lose a defeat), so attacker loses half their force.
    """
    cs = gs.compound_state
    if cs is None:
        gs.compound_state = None
        return

    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    if attacker is None:
        gs.compound_state = None
        return

    is_bandit_campaign = (defender == -1)
    attacker_player = gs.players[attacker]

    # Determine who lost: attacker loses when attack_result <= defense_result
    attacker_lost = cs.campaign_attack_result <= cs.campaign_defense_result

    # For bandit campaigns, only the attacker can lose (bandits are never defeated)
    if is_bandit_campaign or attacker_lost:
        # Attacker's force = warbands on their board
        force = attacker_player.warbands_board
        losses = force // 2

        # Remove losses from attacker's board
        attacker_player.warbands_board -= losses
        attacker_player.warbands_bank += losses

        # Reduce warbands at attacker's site correspondingly
        attacker_site = gs.sites[attacker_player.pawn_site]
        if attacker_site.ruling_player == attacker:
            site_losses = min(losses, attacker_site.warbands)
            attacker_site.warbands -= site_losses
            if attacker_site.warbands <= 0:
                attacker_site.warbands = 0
                attacker_site.ruling_player = None
                attacker_site.warband_color = None
    else:
        # Defender lost — calculate defender's force
        # (This branch cannot be reached for bandit campaigns since bandits
        # never lose; the attacker always loses vs bandits on defeat.)
        if is_bandit_campaign or defender is None or defender < 0:
            gs.compound_state = None
            return

        defender_player = gs.players[defender]
        targeted_site_indices = list(cs.campaign_target_sites)

        # Warbands at targeted sites
        site_warbands = {}
        force = 0
        for site_idx in targeted_site_indices:
            site = gs.sites[site_idx]
            # Only count warbands belonging to defender (site.ruling_player)
            if site.ruling_player == defender:
                site_warbands[site_idx] = site.warbands
                force += site.warbands

        # Defender's board warbands count if pawn is at a relevant site
        defender_at_relevant_site = (
            defender_player.pawn_site == attacker_player.pawn_site
            or defender_player.pawn_site in targeted_site_indices
        )
        board_in_force = defender_player.warbands_board if defender_at_relevant_site else 0
        force += board_in_force

        losses = force // 2
        remaining_losses = losses

        # Remove from targeted sites first
        for site_idx in targeted_site_indices:
            if remaining_losses <= 0:
                break
            if site_idx not in site_warbands:
                continue
            site = gs.sites[site_idx]
            can_remove = min(remaining_losses, site_warbands[site_idx])
            site.warbands -= can_remove
            defender_player.warbands_board -= can_remove
            defender_player.warbands_bank += can_remove
            remaining_losses -= can_remove
            # Update ruling if site is now empty
            if site.warbands <= 0:
                site.warbands = 0
                site.ruling_player = None
                site.warband_color = None

        # Remove remaining from board if defender's board was in the force
        if remaining_losses > 0 and board_in_force > 0:
            board_remove = min(remaining_losses, defender_player.warbands_board)
            defender_player.warbands_board -= board_remove
            defender_player.warbands_bank += board_remove
            # Also reduce warbands at defender's pawn site
            defender_site = gs.sites[defender_player.pawn_site]
            if defender_site.ruling_player == defender:
                site_remove = min(board_remove, defender_site.warbands)
                defender_site.warbands -= site_remove
                if defender_site.warbands <= 0:
                    defender_site.warbands = 0
                    defender_site.ruling_player = None
                    defender_site.warband_color = None

    gs.compound_state = None


def recalculate_oathkeeper(gs: GameState) -> None:
    """Recalculate who holds the Oathkeeper title based on the current oath goal.

    Per §2.11, the title is always held by the player who meets the Oathkeeper
    goal. When the title changes hands, it flips to its Oathkeeper side.
    """
    goal = gs.oath_goal

    if goal == OathGoal.SUPREMACY:
        # §2.11: Chancellor always holds the Oathkeeper of Supremacy;
        # all Imperial players share its power
        chancellor_idx = gs.chancellor_index
        if gs.oathkeeper_holder != chancellor_idx:
            _transfer_oathkeeper(gs, chancellor_idx)

    elif goal == OathGoal.PEOPLE:
        # Whoever holds the People's Favor
        holder = gs.peoples_favor_holder
        if holder is not None and holder != gs.oathkeeper_holder:
            _transfer_oathkeeper(gs, holder)

    elif goal == OathGoal.DEVOTION:
        # Whoever holds the Darkest Secret
        holder = gs.darkest_secret_holder
        if holder is not None and holder != gs.oathkeeper_holder:
            _transfer_oathkeeper(gs, holder)

    elif goal == OathGoal.SANCTUARY:
        # "Protection" in official rules (§2.11) — most relics + banners
        best = None
        best_count = 0
        for i in range(gs.num_players):
            count = _count_relics_and_banners(gs, i)
            if count > best_count:
                best = i
                best_count = count
        if best is not None and best != gs.oathkeeper_holder:
            _transfer_oathkeeper(gs, best)


def _transfer_oathkeeper(gs: GameState, new_holder: int) -> None:
    """Transfer the Oathkeeper title to a new holder.

    Per §2.11, whenever a player takes the title, it flips to its
    Oathkeeper side. The flip to Usurper only happens during the
    Exile's Wake phase (§4.1.3).
    """
    gs.oathkeeper_holder = new_holder
    gs.oathkeeper_side = TitleSide.OATHKEEPER


def _count_relics_and_banners(gs: GameState, player_index: int) -> int:
    """Count relics + banners held by a player (for Sanctuary goal)."""
    count = len(gs.players[player_index].relics)
    if gs.peoples_favor_holder == player_index:
        count += 1
    if gs.darkest_secret_holder == player_index:
        count += 1
    return count


def can_banish_travel_to(gs: GameState, defender_index: int, site_index: int) -> bool:
    """Check if banished player can be sent to a given site (§5.5.7.III).

    Rules: "You can only make them travel to a site they are able to travel to."
    Banish travel is free (no supply cost), so the only restrictions are:
    - Site must exist and be faceup
    - Cannot send to defender's current site
    """
    if site_index < 0 or site_index >= len(gs.sites):
        return False
    site = gs.sites[site_index]
    if not site.is_faceup:
        return False
    defender = gs.players[defender_index]
    if defender.pawn_site == site_index:
        return False
    # §4.1.4 / §5.5.7.III: Shrouded Wood site power blocks forced travel (banish).
    # If the defender's pawn is at a Shrouded Wood site, banish travel is skipped.
    defender_site = gs.sites[defender.pawn_site]
    if defender_site.site_id == SHROUDED_WOOD_ID:
        return False
    return True


def execute_banish_travel(gs: GameState, player_index: int, site_index: int) -> GameState:
    """Attacker chooses a site to banish defender to (§5.5.7.III)."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BANISH_TRAVEL:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in banish travel state")

    defender = cs.banish_target
    if defender is None:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("No banish target")

    if not can_banish_travel_to(gs, defender, site_index):
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError(f"Cannot banish to site {site_index}")

    gs.players[defender].pawn_site = site_index
    cs.state_type = CompoundStateType.CAMPAIGN_BANISH_BURN
    return gs


def execute_banish_skip_travel(gs: GameState, player_index: int) -> GameState:
    """Attacker declines to move the banished player (§5.5.7.III: "may")."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BANISH_TRAVEL:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in banish travel state")

    cs.state_type = CompoundStateType.CAMPAIGN_BANISH_BURN
    return gs


def execute_banish_burn(gs: GameState, player_index: int) -> GameState:
    """Attacker chooses to burn half defender's favor (§5.5.7.III)."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BANISH_BURN:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in banish burn state")

    defender = cs.banish_target
    if defender is not None:
        # Burn half of favor, rounded down — secrets NOT burned
        player = gs.players[defender]
        lost_favor = player.favor // 2
        player.favor -= lost_favor

    _finish_banish(gs)
    return gs


def execute_banish_skip_burn(gs: GameState, player_index: int) -> GameState:
    """Attacker declines to burn favor (§5.5.7.III: "may")."""
    cs = gs.compound_state
    if cs is None or cs.state_type != CompoundStateType.CAMPAIGN_BANISH_BURN:
        from oath.engine.actions import IllegalActionError
        raise IllegalActionError("Not in banish burn state")

    _finish_banish(gs)
    return gs


def _finish_banish(gs: GameState) -> None:
    """Complete banishment resolution and clean up compound state."""
    recalculate_oathkeeper(gs)
    gs.compound_state = None

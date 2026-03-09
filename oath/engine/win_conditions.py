"""Win condition checks for Oath simulator.

Handles all 4 oath types, Oathkeeper/Usurper mechanics,
vision completion, successor goals, and end-of-round die rolls.
"""

from __future__ import annotations

import logging
from typing import Optional

from oath.enums import (
    OathGoal, SuccessorGoal, TitleSide, Role, WinType, MAX_ROUNDS,
)
from oath.cards.database import GRAND_SCEPTER_ID
from oath.state.game_state import GameState

logger = logging.getLogger(__name__)


def check_end_of_round_win(gs: GameState) -> Optional[int]:
    """Check if the game ends at end of round.

    Returns winner player index or None if game continues.
    Called after each complete round (all players have taken turns).
    """
    if gs.round_number < 5:
        return None

    # Roll end-of-game die
    end_probability = _end_probability(gs.round_number)
    roll = gs.rng.random()

    logger.debug(
        "End-of-round die: round=%d, prob=%.2f, roll=%.3f",
        gs.round_number, end_probability, roll,
    )

    if roll >= end_probability and gs.round_number < MAX_ROUNDS:
        logger.debug("Game continues (roll >= prob)")
        return None

    # Game ends — determine winner
    winner = _determine_winner(gs)
    logger.info(
        "Game ending: round=%d, winner=P%d, win_type=%s",
        gs.round_number, winner, gs.win_type,
    )
    return winner


def check_usurper_win(gs: GameState, player_index: int) -> bool:
    """Check if an Exile holding the Usurper title wins at start of their turn.

    Only Exiles can win as Usurper. Citizens are allied with the Chancellor
    and win via the Successor goal instead.
    """
    player = gs.players[player_index]
    if player.role != Role.EXILE:
        return False
    if gs.oathkeeper_holder != player_index:
        return False
    if gs.oathkeeper_side != TitleSide.USURPER:
        return False
    return True


def check_vision_win(gs: GameState, player_index: int) -> bool:
    """Check if a player with a revealed Vision wins.

    An Exile with a revealed Vision wins if they meet the Vision's
    condition at the start of their turn (after enough visions drawn).
    """
    player = gs.players[player_index]
    if player.revealed_vision is None:
        return False
    if player.role not in (Role.EXILE, Role.CITIZEN):
        return False
    if gs.visions_drawn < 3:
        return False

    return _check_vision_condition(gs, player_index, player.revealed_vision)


def check_start_of_turn_wins(gs: GameState, player_index: int) -> Optional[int]:
    """Check all start-of-turn win conditions.

    Returns winner index or None. Also sets gs.win_type.
    """
    # Usurper win check
    if check_usurper_win(gs, player_index):
        gs.win_type = WinType.USURPER
        logger.info("Usurper win: P%d", player_index)
        return player_index

    # Vision win check
    if check_vision_win(gs, player_index):
        gs.win_type = WinType.VISION
        logger.info("Vision win: P%d (vision=%s)", player_index, gs.players[player_index].revealed_vision)
        return player_index

    return None


def _determine_winner(gs: GameState) -> int:
    """Determine the winner when the game ends by die roll or round 8.

    Follows §3.4 War Exhaustion priority order:
    1. §3.4.1 Empire if Oathkeeper — Chancellor/Citizen is Oathkeeper
    2. §3.4.2 Usurper — any Exile holds Usurper title
    3. §3.4.3 Visionary — any Exile has revealed Vision meeting goal
    4. §3.4.4 Empire fallback — Chancellor wins (Citizen successor override)

    Also sets gs.win_type to indicate how the winner won.
    """
    holder = gs.oathkeeper_holder if gs.oathkeeper_holder is not None else gs.chancellor_index

    # §3.4.1 Empire if Oathkeeper: Chancellor or Citizen is the Oathkeeper
    holder_player = gs.players[holder]
    if holder_player.role in (Role.CHANCELLOR, Role.CITIZEN):
        # Citizen successor override: if a Citizen meets successor goal, they win instead
        for i, player in enumerate(gs.players):
            if player.role == Role.CITIZEN and _check_successor_goal(gs, i):
                gs.win_type = WinType.SUCCESSOR
                logger.info("§3.4.1 Successor win: P%d (goal=%s)", i, gs.successor_goal.name)
                return i
        # Otherwise Oathkeeper wins
        gs.win_type = WinType.OATHKEEPER_DEFAULT
        logger.info("§3.4.1 Empire Oathkeeper win: P%d", holder)
        return holder

    # §3.4.2 Usurper: any Exile with Usurper title wins
    if (gs.oathkeeper_side == TitleSide.USURPER and
            gs.oathkeeper_holder is not None and
            gs.players[gs.oathkeeper_holder].role == Role.EXILE):
        gs.win_type = WinType.USURPER
        logger.info("§3.4.2 Usurper win: P%d", gs.oathkeeper_holder)
        return gs.oathkeeper_holder

    # §3.4.3 Visionary: any Exile with revealed Vision meeting goal
    # Tiebreaker: Conquest(221) > Rebellion(223) > Sanctuary(224) > Faith(222)
    vision_priority = [221, 223, 224, 222]
    for vision_id in vision_priority:
        for i, player in enumerate(gs.players):
            if (player.role == Role.EXILE and
                    player.revealed_vision == vision_id and
                    _check_vision_condition(gs, i, vision_id)):
                gs.win_type = WinType.VISION
                logger.info("§3.4.3 Visionary win: P%d (vision=%d)", i, vision_id)
                return i

    # §3.4.4 Empire fallback: Chancellor wins, Citizen successor override
    for i, player in enumerate(gs.players):
        if player.role == Role.CITIZEN and _check_successor_goal(gs, i):
            gs.win_type = WinType.SUCCESSOR
            logger.info("§3.4.4 Successor win: P%d (goal=%s)", i, gs.successor_goal.name)
            return i

    gs.win_type = WinType.OATHKEEPER_DEFAULT
    logger.info("§3.4.4 Empire fallback win: P%d (Chancellor)", gs.chancellor_index)
    return gs.chancellor_index


def _end_probability(round_number: int) -> float:
    """Probability the game ends at end of this round."""
    if round_number < 5:
        return 0.0
    elif round_number == 5:
        return 1.0 / 6.0
    elif round_number == 6:
        return 2.0 / 6.0
    elif round_number == 7:
        return 4.0 / 6.0
    else:
        return 1.0  # Round 8 always ends


def _check_vision_condition(gs: GameState, player_index: int, vision_id: int) -> bool:
    """Check if a player meets a specific Vision's win condition."""
    player = gs.players[player_index]

    # Vision of Conquest (221): Rule the most sites
    if vision_id == 221:
        my_sites = gs.count_sites_ruled(player_index)
        if my_sites == 0:
            return False
        for i in range(gs.num_players):
            if i != player_index and gs.count_sites_ruled(i) >= my_sites:
                return False
        return True

    # Vision of Faith (222): Hold the Darkest Secret
    elif vision_id == 222:
        return gs.darkest_secret_holder == player_index

    # Vision of Rebellion (223): Hold the People's Favor
    elif vision_id == 223:
        return gs.peoples_favor_holder == player_index

    # Vision of Sanctuary (224): Hold the most relics + banners
    elif vision_id == 224:
        my_count = _count_relics_and_banners(gs, player_index)
        if my_count == 0:
            return False
        for i in range(gs.num_players):
            if i != player_index and _count_relics_and_banners(gs, i) >= my_count:
                return False
        return True

    # Vision of Conspiracy (225): Have the most secrets
    elif vision_id == 225:
        if player.secrets == 0:
            return False
        for i in range(gs.num_players):
            if i != player_index and gs.players[i].secrets >= player.secrets:
                return False
        return True

    return False


def _check_successor_goal(gs: GameState, player_index: int) -> bool:
    """Check if a Citizen meets the successor goal (§3.3.1)."""
    goal = gs.successor_goal

    if goal == SuccessorGoal.MOST_RELICS_BANNERS:
        # Supremacy successor: hold more relics+banners than Chancellor AND any other Citizen
        my_count = _count_relics_and_banners(gs, player_index)
        chancellor_count = _count_relics_and_banners(gs, gs.chancellor_index)
        if my_count <= chancellor_count:
            return False
        # Also must beat all other Citizens
        for i, p in enumerate(gs.players):
            if i != player_index and p.role == Role.CITIZEN:
                if _count_relics_and_banners(gs, i) >= my_count:
                    return False
        return True

    elif goal == SuccessorGoal.DARKEST_SECRET:
        # People successor: hold Darkest Secret
        return gs.darkest_secret_holder == player_index

    elif goal == SuccessorGoal.PEOPLES_FAVOR:
        # Sanctuary/Protection successor: hold People's Favor
        return gs.peoples_favor_holder == player_index

    elif goal == SuccessorGoal.GRAND_SCEPTER:
        # Devotion successor: hold Grand Scepter (§3.3.1)
        return GRAND_SCEPTER_ID in gs.players[player_index].relics

    return False


def _count_relics_and_banners(gs: GameState, player_index: int) -> int:
    """Count relics + banners held by a player."""
    count = len(gs.players[player_index].relics)
    if gs.peoples_favor_holder == player_index:
        count += 1
    if gs.darkest_secret_holder == player_index:
        count += 1
    return count

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

    Also sets gs.win_type to indicate how the winner won.
    """
    # Check if any exile has met their vision condition
    for i, player in enumerate(gs.players):
        if player.role in (Role.EXILE, Role.CITIZEN) and player.revealed_vision is not None:
            if _check_vision_condition(gs, i, player.revealed_vision):
                gs.win_type = WinType.VISION
                logger.info("End-of-round vision win: P%d (%s) vision=%d", i, player.role.name, player.revealed_vision)
                return i

    # Check successor goal for citizens
    for i, player in enumerate(gs.players):
        if player.role == Role.CITIZEN:
            if _check_successor_goal(gs, i):
                gs.win_type = WinType.SUCCESSOR
                logger.info("Successor win: P%d (goal=%s)", i, gs.successor_goal.name)
                return i

    # Default: Oathkeeper wins
    gs.win_type = WinType.OATHKEEPER_DEFAULT
    holder = gs.oathkeeper_holder if gs.oathkeeper_holder is not None else gs.chancellor_index
    logger.info("Oathkeeper default win: P%d", holder)
    if gs.oathkeeper_holder is not None:
        return gs.oathkeeper_holder

    # Fallback: Chancellor
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
    """Check if a Citizen meets the successor goal."""
    goal = gs.successor_goal

    if goal == SuccessorGoal.MOST_SITES:
        my_sites = gs.count_sites_ruled(player_index)
        chancellor_sites = gs.count_sites_ruled(gs.chancellor_index)
        return my_sites > chancellor_sites

    elif goal == SuccessorGoal.MOST_RELICS_BANNERS:
        my_count = _count_relics_and_banners(gs, player_index)
        chancellor_count = _count_relics_and_banners(gs, gs.chancellor_index)
        return my_count > chancellor_count

    elif goal == SuccessorGoal.DARKEST_SECRET:
        return gs.darkest_secret_holder == player_index

    elif goal == SuccessorGoal.PEOPLES_FAVOR:
        return gs.peoples_favor_holder == player_index

    return False


def _count_relics_and_banners(gs: GameState, player_index: int) -> int:
    """Count relics + banners held by a player."""
    count = len(gs.players[player_index].relics)
    if gs.peoples_favor_holder == player_index:
        count += 1
    if gs.darkest_secret_holder == player_index:
        count += 1
    return count

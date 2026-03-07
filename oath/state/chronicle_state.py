"""Chronicle state for persisting between games.

The ChronicleState holds all information that carries over between
games in Oath's legacy system (Section 8 of the Law of Oath).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from oath.enums import OathGoal, SuccessorGoal, Role, Suit


@dataclass
class ChronicleSiteSnapshot:
    """Snapshot of a site and its attached cards for chronicle persistence."""
    site_id: int
    cards: list[int] = field(default_factory=list)       # denizen/edifice card_ids
    relics: list[int] = field(default_factory=list)       # relic card_ids at site
    has_edifice: bool = False
    edifice_ruined: bool = False


@dataclass
class ChronicleState:
    """Persistent state between games.

    This represents the "World Box" contents — the physical state
    of the game components that carry over between chronicles.
    """
    # The Archive: cards organized by suit available to add to world deck
    archive: dict[int, list[int]] = field(default_factory=lambda: {s: [] for s in range(6)})

    # Dispossessed section of Archive (cards removed from active rotation)
    dispossessed: dict[int, list[int]] = field(default_factory=lambda: {s: [] for s in range(6)})

    # Chronicled map: ordered site snapshots (bottom Hinterland to top Cradle)
    chronicled_sites: list[ChronicleSiteSnapshot] = field(default_factory=list)

    # Site deck (facedown sites not on the map)
    site_deck: list[int] = field(default_factory=list)

    # Relic deck carried forward
    relic_deck: list[int] = field(default_factory=list)

    # World deck (rebuilt at end of chronicle)
    world_deck: list[int] = field(default_factory=list)

    # The oath goal for next game
    oath_goal: OathGoal = OathGoal.SUPREMACY

    # Successor goal (derived from oath_goal)
    successor_goal: SuccessorGoal = SuccessorGoal.MOST_SITES

    # Player boards (which side: Exile or Citizen) for next game
    # Index 0 = player 1 (non-Chancellor players only)
    player_boards: list[Role] = field(default_factory=list)

    # Edifice card_ids currently on the map (intact or ruined)
    edifices_in_play: list[int] = field(default_factory=list)

    # Who won the last game (player index)
    last_winner: Optional[int] = None

    # How many games have been played in this chronicle
    games_played: int = 0

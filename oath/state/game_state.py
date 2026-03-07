"""Core GameState dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from oath.enums import (
    OathGoal, SuccessorGoal, TitleSide, Phase, CompoundStateType,
    Role, Region, ActionType, MAX_ROUNDS,
)
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState


@dataclass
class ActionRecord:
    """Record of a single action taken."""
    player_index: int
    action_type: ActionType
    target_site: Optional[int] = None
    target_player: Optional[int] = None
    was_successful: bool = False


@dataclass
class CompoundState:
    """Sub-state for multi-step compound actions."""
    state_type: CompoundStateType
    # Search state
    drawn_cards: list[int] = field(default_factory=list)
    search_source: Optional[str] = None  # "deck" or "discard"
    cards_remaining: list[bool] = field(default_factory=list)  # Which drawn cards not yet played
    # Campaign state
    campaign_attacker: Optional[int] = None
    campaign_defender: Optional[int] = None
    campaign_targets: list[str] = field(default_factory=list)  # "site", "relic:N", "pawn"
    campaign_target_sites: list[int] = field(default_factory=list)
    campaign_attack_dice: int = 0
    campaign_defense_dice: int = 0
    campaign_attack_result: int = 0
    campaign_defense_result: int = 0
    # Citizenship state
    citizenship_offerer: Optional[int] = None
    citizenship_target: Optional[int] = None
    reliquary_slot: Optional[int] = None


@dataclass
class GameState:
    """Complete state of an Oath game."""
    # Players
    players: list[PlayerState] = field(default_factory=list)
    num_players: int = 4
    current_player_index: int = 0
    turn_order: list[int] = field(default_factory=list)

    # Map
    sites: list[SiteState] = field(default_factory=list)

    # Decks
    world_deck: list[int] = field(default_factory=list)
    discard_piles: list[list[int]] = field(default_factory=lambda: [[], [], []])
    relic_deck: list[int] = field(default_factory=list)

    # Banks
    favor_banks: list[int] = field(default_factory=lambda: [0] * 6)
    shared_secrets: int = 0

    # Banners
    peoples_favor_holder: Optional[int] = None
    peoples_favor_tokens: int = 1
    peoples_favor_is_mob: bool = False
    darkest_secret_holder: Optional[int] = None
    darkest_secret_tokens: int = 1

    # Title
    oathkeeper_holder: Optional[int] = None
    oathkeeper_side: TitleSide = TitleSide.OATHKEEPER

    # Goals
    oath_goal: OathGoal = OathGoal.SUPREMACY
    successor_goal: SuccessorGoal = SuccessorGoal.MOST_SITES

    # Reliquary
    reliquary: list[int] = field(default_factory=list)

    # Round tracking
    round_number: int = 1
    visions_drawn: int = 0
    turn_in_round: int = 0  # Which player's turn within the round

    # Phase & compound state
    phase: Phase = Phase.WAKE
    compound_state: Optional[CompoundState] = None

    # History
    action_history: list[ActionRecord] = field(default_factory=list)

    # RNG
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng())

    # Game over
    is_game_over: bool = False
    winner: Optional[int] = None

    # Supply spent this turn
    supply_spent_this_turn: int = 0
    actions_taken_this_turn: int = 0

    # Citizenship offer pending
    pending_citizenship_target: Optional[int] = None

    @property
    def in_compound_action(self) -> bool:
        return self.compound_state is not None

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def count_sites_ruled(self, player_index: int) -> int:
        return sum(1 for s in self.sites if s.ruling_player == player_index and s.is_faceup)

    def get_player_site(self, player_index: int) -> SiteState:
        return self.sites[self.players[player_index].pawn_site]

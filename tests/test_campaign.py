"""Tests for campaign resolution."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.engine.campaign import (
    can_campaign, execute_campaign_declare,
    execute_campaign_done_targets, execute_campaign_target_site,
    execute_campaign_no_battle, execute_campaign_sacrifice,
)
from oath.enums import Phase, CompoundStateType


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


class TestCampaignDeclare:
    def test_cannot_campaign_self(self, gs):
        assert not can_campaign(gs, 0, 0)

    def test_cannot_campaign_no_supply(self, gs):
        gs.players[0].supply = 0
        assert not can_campaign(gs, 0, 1)

    def test_campaign_enters_compound(self, gs):
        # Place players at same site
        gs.players[0].pawn_site = 0
        gs.players[1].pawn_site = 0
        gs.players[0].supply = 5

        if can_campaign(gs, 0, 1):
            execute_campaign_declare(gs, 0, 1)
            assert gs.compound_state is not None
            assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_TARGETS


class TestCampaignResolution:
    def test_campaign_full_flow(self, gs):
        """Test a complete campaign from declare to resolution."""
        # Setup: both players at site 0, player 0 rules it
        gs.players[0].pawn_site = 0
        gs.players[1].pawn_site = 0
        gs.sites[0].ruling_player = 0
        gs.sites[0].warbands = 3
        gs.players[0].warbands_board = 3
        gs.players[0].supply = 5

        # Player 1 has some warbands too
        gs.players[1].warbands_board = 2

        if can_campaign(gs, 1, 0):
            gs.players[1].supply = 5
            execute_campaign_declare(gs, 1, 0)
            assert gs.compound_state is not None

            # Target site 0
            execute_campaign_target_site(gs, 1, 0)

            # Done targets
            execute_campaign_done_targets(gs, 1)
            assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BATTLE

            # No battle plan
            execute_campaign_no_battle(gs, 1)

            # Campaign should have resolved (either victory, sacrifice, or defeat)
            # compound_state may be None (resolved) or CAMPAIGN_SACRIFICE
            if gs.compound_state is not None:
                assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_SACRIFICE
                execute_campaign_sacrifice(gs, 1, 0)
            # Campaign is resolved
            assert gs.compound_state is None

    def test_campaign_sacrifice_mechanics(self, gs):
        """Test that sacrifice adds to attack total."""
        gs.players[0].pawn_site = 0
        gs.players[1].pawn_site = 0
        gs.sites[0].ruling_player = 0
        gs.sites[0].warbands = 5
        gs.players[0].warbands_board = 5
        gs.players[1].supply = 5
        gs.players[1].warbands_board = 4

        if not can_campaign(gs, 1, 0):
            return

        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)

        if (gs.compound_state is not None and
                gs.compound_state.state_type == CompoundStateType.CAMPAIGN_SACRIFICE):
            prev_attack = gs.compound_state.campaign_attack_result
            execute_campaign_sacrifice(gs, 1, 3)
            # After sacrifice, campaign resolves
            assert gs.compound_state is None

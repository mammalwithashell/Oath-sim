"""Tests for major actions: Travel, Search, Muster, Trade, Recover."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.engine.actions import (
    can_travel, execute_travel, travel_cost,
    can_muster, execute_muster,
    can_trade_favor, execute_trade_favor,
    can_trade_secrets, execute_trade_secrets,
    can_search_deck, execute_search,
    can_recover_relic, execute_recover_relic,
    can_recover_peoples_favor, execute_recover_peoples_favor,
    can_recover_darkest_secret, execute_recover_darkest_secret,
    execute_search_play, execute_search_discard,
    execute_end_act_phase, IllegalActionError,
)
from oath.enums import Phase, Role, Region


@pytest.fixture
def gs():
    """Create a fresh game state for testing."""
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


class TestTravel:
    def test_travel_to_different_site(self, gs):
        player = gs.players[0]
        initial_supply = player.supply
        initial_site = player.pawn_site

        # Find a legal target
        for target in range(8):
            if can_travel(gs, 0, target):
                execute_travel(gs, 0, target)
                assert player.pawn_site == target
                assert player.supply < initial_supply
                break

    def test_travel_cost_same_region(self, gs):
        # Both cradle sites are region 0
        gs.players[0].pawn_site = 0
        cost = travel_cost(gs, 0, 1)
        assert cost == 1

    def test_travel_cost_cross_region(self, gs):
        gs.players[0].pawn_site = 0  # Cradle
        # Site 2 is Provinces
        cost = travel_cost(gs, 0, 2)
        assert cost == 1  # Cradle(0) to Provinces(1) = 1

    def test_cannot_travel_same_site(self, gs):
        site = gs.players[0].pawn_site
        assert not can_travel(gs, 0, site)

    def test_cannot_travel_no_supply(self, gs):
        gs.players[0].supply = 0
        assert not can_travel(gs, 0, 1)

    def test_cannot_travel_during_compound(self, gs):
        from oath.state.game_state import CompoundState
        from oath.enums import CompoundStateType
        gs.compound_state = CompoundState(state_type=CompoundStateType.SEARCH_CHOOSE)
        assert not can_travel(gs, 0, 1)

    def test_travel_reveals_facedown_site(self, gs):
        # Find a facedown site
        for i, site in enumerate(gs.sites):
            if not site.is_faceup and site.site_id != 0:
                gs.players[0].supply = 10
                if can_travel(gs, 0, i):
                    execute_travel(gs, 0, i)
                    assert gs.sites[i].is_faceup
                    break


class TestMuster:
    def test_muster_places_warbands(self, gs):
        player = gs.players[0]
        site = gs.sites[player.pawn_site]
        initial_warbands = site.warbands
        initial_bank = player.warbands_bank

        # Need a card at site and to rule it
        site.ruling_player = 0
        if site.cards[0] is not None:
            execute_muster(gs, 0, 0)
            assert site.warbands > initial_warbands
            assert player.warbands_bank < initial_bank

    def test_muster_costs_supply(self, gs):
        player = gs.players[0]
        site = gs.sites[player.pawn_site]
        site.ruling_player = 0
        initial_supply = player.supply

        if site.cards[0] is not None:
            execute_muster(gs, 0, 0)
            assert player.supply == initial_supply - 1

    def test_cannot_muster_no_supply(self, gs):
        gs.players[0].supply = 0
        assert not can_muster(gs, 0, 0)


class TestTradeFavor:
    def test_trade_favor_gains_favor(self, gs):
        player = gs.players[0]
        player.secrets = 3
        site = gs.sites[player.pawn_site]

        if site.cards[0] is not None:
            from oath.cards.database import get_card
            card_data = get_card(site.cards[0])
            if card_data.suit is not None:
                gs.favor_banks[int(card_data.suit)] = 5
                initial_favor = player.favor
                if can_trade_favor(gs, 0, 0):
                    execute_trade_favor(gs, 0, 0)
                    assert player.favor > initial_favor
                    assert player.secrets < 3

    def test_cannot_trade_favor_no_secrets(self, gs):
        gs.players[0].secrets = 0
        assert not can_trade_favor(gs, 0, 0)


class TestTradeSecrets:
    def test_trade_secrets_gains_secrets(self, gs):
        player = gs.players[0]
        player.favor = 3
        gs.shared_secrets = 10
        site = gs.sites[player.pawn_site]

        if site.cards[0] is not None:
            initial_secrets = player.secrets
            if can_trade_secrets(gs, 0, 0):
                execute_trade_secrets(gs, 0, 0)
                assert player.secrets > initial_secrets

    def test_cannot_trade_secrets_no_favor(self, gs):
        gs.players[0].favor = 0
        assert not can_trade_secrets(gs, 0, 0)


class TestSearch:
    def test_search_deck_enters_compound(self, gs):
        player = gs.players[0]
        player.supply = 5
        if can_search_deck(gs, 0):
            execute_search(gs, 0, "deck")
            assert gs.compound_state is not None or len(gs.world_deck) == 0

    def test_search_costs_supply(self, gs):
        player = gs.players[0]
        player.supply = 5
        initial_supply = player.supply
        if can_search_deck(gs, 0):
            execute_search(gs, 0, "deck")
            assert player.supply < initial_supply

    def test_cannot_search_no_supply(self, gs):
        gs.players[0].supply = 0
        assert not can_search_deck(gs, 0)


class TestRecover:
    def test_recover_relic_moves_to_player(self, gs):
        player = gs.players[0]
        site = gs.sites[player.pawn_site]
        site.ruling_player = 0
        site.relics = [211]  # Grand Scepter

        initial_relics = len(player.relics)
        execute_recover_relic(gs, 0, 0)
        assert len(player.relics) == initial_relics + 1
        assert 211 in player.relics

    def test_recover_requires_ruling(self, gs):
        player = gs.players[0]
        site = gs.sites[player.pawn_site]
        site.ruling_player = 1  # Someone else rules
        site.relics = [211]
        assert not can_recover_relic(gs, 0, 0)


class TestEndAct:
    def test_end_act_changes_phase(self, gs):
        execute_end_act_phase(gs, 0)
        assert gs.phase == Phase.REST

    def test_cannot_end_act_during_compound(self, gs):
        from oath.state.game_state import CompoundState
        from oath.enums import CompoundStateType
        gs.compound_state = CompoundState(state_type=CompoundStateType.SEARCH_CHOOSE)
        with pytest.raises(IllegalActionError):
            execute_end_act_phase(gs, 0)

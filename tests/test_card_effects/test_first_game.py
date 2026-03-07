"""Tests for first-game denizen card effects (IDs 1-19)."""

import pytest
from oath.cards.effects import (
    get_effects, get_action_effects, get_battle_plan_effects,
    get_when_played_effects, get_rest_effects, get_modifier_effects,
)
from oath.cards.effects._helpers import gain_warbands
from oath.enums import (
    EffectTrigger, ModifierType, Phase, Role, Suit,
    CompoundStateType, MAX_ADVISERS,
)
from oath.state.game_state import CompoundState
from oath.engine.game import create_initial_state, do_rest_phase
from oath.engine.actions import travel_cost, execute_use_card_action
from oath.cards.database import get_card


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


@pytest.fixture
def setup_adviser():
    def _setup(gs, player_index, card_id, slot=0):
        gs.players[player_index].advisers[slot] = card_id
        gs.players[player_index].adviser_faceup[slot] = True
        return gs
    return _setup


# ── Registration Tests ────────────────────────────────────────────

class TestEffectRegistration:
    def test_longbows_registered(self):
        effects = get_effects(1)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.BATTLE_PLAN

    def test_taming_charm_registered(self):
        effects = get_effects(2)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.ACTION

    def test_elders_registered(self):
        effects = get_effects(3)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.ACTION

    def test_forest_paths_registered(self):
        effects = get_effects(4)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_animal_playmates_registered(self):
        effects = get_effects(5)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_naysayers_registered(self):
        effects = get_effects(6)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.REST

    def test_a_small_favor_registered(self):
        effects = get_effects(7)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.WHEN_PLAYED

    def test_garrison_registered(self):
        effects = get_effects(8)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.WHEN_PLAYED

    def test_errand_boy_registered(self):
        effects = get_effects(9)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_old_oak_registered(self):
        effects = get_effects(10)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_alchemist_registered(self):
        effects = get_effects(11)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.ACTION

    def test_scryer_registered(self):
        effects = get_effects(12)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.ACTION

    def test_bear_traps_registered(self):
        effects = get_effects(13)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.BATTLE_PLAN

    def test_wayside_inn_registered(self):
        effects = get_effects(14)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.ACTION

    def test_keep_registered(self):
        effects = get_effects(15)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.BATTLE_PLAN

    def test_tents_registered(self):
        effects = get_effects(16)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_wrestlers_registered(self):
        effects = get_effects(17)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.BATTLE_PLAN

    def test_pressgangs_registered(self):
        effects = get_effects(18)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.MODIFIER

    def test_sticky_fire_registered(self):
        effects = get_effects(19)
        assert len(effects) == 1
        assert effects[0].trigger == EffectTrigger.BATTLE_PLAN


# ── Action Effect Tests ──────────────────────────────────────────

class TestAlchemist:
    def test_gains_4_favor(self, gs, setup_adviser):
        setup_adviser(gs, 0, 11)  # Alchemist as adviser
        gs.favor_banks = [6, 6, 6, 6, 6, 6]
        initial_favor = gs.players[0].favor
        effect = get_action_effects(11)[0]
        gs = effect.execute(gs, 0)
        assert gs.players[0].favor == initial_favor + 4


class TestElders:
    def test_gains_1_favor(self, gs, setup_adviser):
        setup_adviser(gs, 0, 3)
        gs.favor_banks = [6, 6, 6, 6, 6, 6]
        initial_favor = gs.players[0].favor
        effect = get_action_effects(3)[0]
        gs = effect.execute(gs, 0)
        assert gs.players[0].favor == initial_favor + 1


class TestWaysideInn:
    def test_gains_2_supply(self, gs, setup_adviser):
        setup_adviser(gs, 0, 14)
        initial_supply = gs.players[0].supply
        effect = get_action_effects(14)[0]
        gs = effect.execute(gs, 0)
        assert gs.players[0].supply == initial_supply + 2


class TestTamingCharm:
    def test_condition_needs_beast_or_nomad_at_site(self, gs, setup_adviser):
        setup_adviser(gs, 0, 2)
        site = gs.sites[gs.players[0].pawn_site]
        # Clear cards
        site.cards = [None, None, None]
        effect = get_action_effects(2)[0]
        assert not effect.condition(gs, 0)

    def test_discards_beast_card_for_favor(self, gs, setup_adviser):
        setup_adviser(gs, 0, 2)
        player = gs.players[0]
        site = gs.sites[player.pawn_site]
        # Place a Beast card at site
        site.cards[0] = 5  # Animal Playmates is Beast
        gs.favor_banks[int(Suit.BEAST)] = 6
        initial_favor = player.favor
        effect = get_action_effects(2)[0]
        gs = effect.execute(gs, 0)
        assert player.favor == initial_favor + 2
        assert site.cards[0] is None  # Card was discarded


# ── When Played Tests ────────────────────────────────────────────

class TestASmallFavor:
    def test_gains_4_warbands(self, gs):
        player = gs.players[0]
        initial_board = player.warbands_board
        initial_bank = player.warbands_bank
        effect = get_when_played_effects(7)[0]
        gs = effect.execute(gs, 0)
        gained = min(4, initial_bank)
        assert player.warbands_board == initial_board + gained
        assert player.warbands_bank == initial_bank - gained


class TestGarrison:
    def test_gains_warbands_per_ruled_site(self, gs):
        player = gs.players[0]
        # Player 0 rules site 0
        gs.sites[0].ruling_player = 0
        gs.sites[0].is_faceup = True
        initial_board = player.warbands_board
        initial_bank = player.warbands_bank
        effect = get_when_played_effects(8)[0]
        gs = effect.execute(gs, 0)
        # Should gain 1 warband (1 ruled site) and place 1 on ruled site
        assert player.warbands_bank < initial_bank


# ── Battle Plan Tests ────────────────────────────────────────────

class TestLongbows:
    def test_adds_attack_die_for_attacker(self, gs):
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_BATTLE,
            campaign_attacker=0,
            campaign_defender=1,
            campaign_attack_dice=3,
            campaign_defense_dice=2,
        )
        effect = get_battle_plan_effects(1)[0]
        gs = effect.execute(gs, 0)
        assert gs.compound_state.campaign_attack_dice == 4

    def test_removes_defense_die_for_defender(self, gs):
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_BATTLE,
            campaign_attacker=0,
            campaign_defender=1,
            campaign_attack_dice=3,
            campaign_defense_dice=2,
        )
        effect = get_battle_plan_effects(1)[0]
        gs = effect.execute(gs, 1)
        assert gs.compound_state.campaign_defense_dice == 1


class TestWrestlers:
    def test_sacrifices_warband_for_die(self, gs):
        player = gs.players[0]
        player.warbands_board = 3
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_BATTLE,
            campaign_attacker=0,
            campaign_defender=1,
            campaign_attack_dice=2,
        )
        effect = get_battle_plan_effects(17)[0]
        gs = effect.execute(gs, 0)
        assert player.warbands_board == 2
        assert gs.compound_state.campaign_attack_dice == 3

    def test_condition_needs_warbands(self, gs):
        gs.players[0].warbands_board = 0
        effect = get_battle_plan_effects(17)[0]
        assert not effect.condition(gs, 0)


class TestBearTraps:
    def test_kills_attacker_warband(self, gs):
        attacker = gs.players[0]
        attacker.warbands_board = 3
        gs.sites[attacker.pawn_site].warbands = 3
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_BATTLE,
            campaign_attacker=0,
            campaign_defender=1,
        )
        effect = get_battle_plan_effects(13)[0]
        gs = effect.execute(gs, 1)
        assert attacker.warbands_board == 2


class TestKeep:
    def test_adds_defense_dice_when_site_targeted(self, gs):
        defender = gs.players[1]
        defender.pawn_site = 1
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_BATTLE,
            campaign_attacker=0,
            campaign_defender=1,
            campaign_targets=["site:1"],
            campaign_defense_dice=2,
        )
        effect = get_battle_plan_effects(15)[0]
        gs = effect.execute(gs, 1)
        assert gs.compound_state.campaign_defense_dice == 4


# ── Modifier Tests ───────────────────────────────────────────────

class TestTents:
    def test_free_travel_same_region(self, gs, setup_adviser):
        setup_adviser(gs, 0, 16)
        # Player 0 is at site 0 (Cradle), travel to site 1 (Cradle)
        gs.players[0].pawn_site = 0
        cost = travel_cost(gs, 0, 1)
        assert cost == 0  # Same region, Tents makes it free


# ── REST Effect Tests ────────────────────────────────────────────

class TestNaysayers:
    def test_condition_true_when_exile_is_oathkeeper(self, gs, setup_adviser):
        setup_adviser(gs, 1, 6)  # Give Naysayers to player 1 (exile)
        gs.oathkeeper_holder = 1  # Exile holds Oathkeeper
        effect = get_rest_effects(6)[0]
        assert effect.condition(gs, 1)

    def test_condition_false_when_chancellor_is_oathkeeper(self, gs, setup_adviser):
        setup_adviser(gs, 1, 6)
        gs.oathkeeper_holder = 0  # Chancellor holds it
        effect = get_rest_effects(6)[0]
        assert not effect.condition(gs, 1)

    def test_takes_favor_from_chancellor(self, gs, setup_adviser):
        setup_adviser(gs, 1, 6)
        gs.oathkeeper_holder = 1
        gs.players[0].favor = 5  # Chancellor has favor
        gs.players[1].favor = 2
        effect = get_rest_effects(6)[0]
        gs = effect.execute(gs, 1)
        assert gs.players[0].favor == 4
        assert gs.players[1].favor == 3

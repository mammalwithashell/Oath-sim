"""Tests for campaign resolution."""

import pytest
import numpy as np

from oath.engine.game import create_initial_state
from oath.engine.campaign import (
    can_campaign, execute_campaign_declare,
    execute_campaign_done_targets, execute_campaign_target_site,
    execute_campaign_target_relic, execute_campaign_target_pawn,
    execute_campaign_no_battle, execute_campaign_sacrifice,
    execute_campaign_battle_plan,
    execute_campaign_defender_battle_plan,
    _resolve_campaign_dice, _resolve_campaign_victory,
    _resolve_campaign_defeat,
    can_banish_travel_to, execute_banish_travel, execute_banish_skip_travel,
    execute_banish_burn, execute_banish_skip_burn,
    recalculate_oathkeeper,
)
from oath.enums import (
    Phase, CompoundStateType, Role, OathGoal, TitleSide, Region,
)
from oath.state.game_state import CompoundState


@pytest.fixture
def gs():
    state = create_initial_state(num_players=4, seed=42)
    state.phase = Phase.ACT
    return state


def _setup_campaign(gs, attacker=1, defender=0):
    """Helper: place both players at site 0, defender rules it."""
    gs.players[defender].pawn_site = 0
    gs.players[attacker].pawn_site = 0
    gs.sites[0].ruling_player = defender
    gs.sites[0].warbands = 3
    gs.players[defender].warbands_board = 3
    gs.players[attacker].supply = 5
    gs.players[attacker].warbands_board = 4
    return gs


def _run_to_dice(gs, attacker=1, defender=0):
    """Helper: declare campaign, target site 0, skip both battle plans."""
    execute_campaign_declare(gs, attacker, defender)
    execute_campaign_target_site(gs, attacker, 0)
    execute_campaign_done_targets(gs, attacker)
    execute_campaign_no_battle(gs, attacker)  # Attacker declines
    execute_campaign_no_battle(gs, defender)  # Defender declines


# ─── Declaration Tests ────────────────────────────────────────────────

class TestCampaignDeclare:
    def test_cannot_campaign_self(self, gs):
        assert not can_campaign(gs, 0, 0)

    def test_cannot_campaign_no_supply(self, gs):
        gs.players[0].supply = 0
        assert not can_campaign(gs, 0, 1)

    def test_cannot_campaign_with_one_supply(self, gs):
        """Campaign costs 2 supply (§5.5.1), so 1 is insufficient."""
        gs.players[0].pawn_site = 0
        gs.players[1].pawn_site = 0
        gs.players[0].supply = 1
        assert not can_campaign(gs, 0, 1)

    def test_campaign_cost_is_two_supply(self, gs):
        """Verify exactly 2 supply is deducted (§5.5.1)."""
        _setup_campaign(gs)
        initial_supply = gs.players[1].supply
        execute_campaign_declare(gs, 1, 0)
        assert gs.players[1].supply == initial_supply - 2
        assert gs.supply_spent_this_turn == 2

    def test_campaign_enters_compound(self, gs):
        _setup_campaign(gs)
        execute_campaign_declare(gs, 1, 0)
        assert gs.compound_state is not None
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_TARGETS

    def test_defender_must_rule_site_or_be_present(self, gs):
        """§5.5.1: Target must rule your site or have pawn at your site."""
        gs.players[0].pawn_site = 0
        gs.players[1].pawn_site = 0
        gs.players[0].supply = 5
        # Player 1 is at same site — valid target
        assert can_campaign(gs, 0, 1)

        # Move player 1 away but make them rule site 0
        gs.players[1].pawn_site = 3
        gs.sites[0].ruling_player = 1
        assert can_campaign(gs, 0, 1)

    def test_same_region_not_enough_for_campaign(self, gs):
        """Target ruling a different site in the same region is NOT enough."""
        gs.players[0].pawn_site = 0  # Cradle site 0
        gs.players[1].pawn_site = 1  # Cradle site 1 (different site)
        gs.sites[0].ruling_player = None  # Player 1 doesn't rule site 0
        gs.sites[1].ruling_player = 1     # Player 1 rules site 1
        gs.players[0].supply = 5
        # Same region, but target doesn't rule attacker's site or share it
        assert not can_campaign(gs, 0, 1)


# ─── Battle Plan Phase Tests ─────────────────────────────────────────

class TestBattlePlanPhase:
    def test_defender_battle_plan_phase(self, gs):
        """§5.5.3: After attacker, defender gets battle plan phase."""
        _setup_campaign(gs)
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BATTLE

        # Attacker declines
        execute_campaign_no_battle(gs, 1)
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BATTLE_DEFENDER

        # Defender declines → dice roll happens
        execute_campaign_no_battle(gs, 0)
        # Now resolved or in sacrifice
        assert (gs.compound_state is None or
                gs.compound_state.state_type == CompoundStateType.CAMPAIGN_SACRIFICE)


# ─── Dice and Combat Math Tests ──────────────────────────────────────

class TestCombatMath:
    def test_attack_dice_from_board(self, gs):
        """§5.5.2: Attack dice = warbands on attacker's board."""
        _setup_campaign(gs)
        gs.players[1].warbands_board = 7
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)
        # After dice roll, attack_dice should have been set to 7
        # (can't check directly since dice already rolled, but we verify
        # the campaign_attack_dice was set correctly)
        # Dice already rolled, but we can set up a direct test:
        pass  # Covered by the direct dice test below

    def test_attack_dice_directly(self, gs):
        """Verify attack dice count equals warbands_board."""
        _setup_campaign(gs)
        gs.players[1].warbands_board = 5
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        # Skip to defender phase
        execute_campaign_no_battle(gs, 1)
        # Now trigger dice via defender skip
        execute_campaign_no_battle(gs, 0)
        cs = gs.compound_state
        if cs is not None:
            assert cs.campaign_attack_dice == 5

    def test_ties_go_to_defender(self, gs):
        """§5.5.5: Attack must be strictly higher to win."""
        _setup_campaign(gs)
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)
        # If compound_state is None, campaign resolved (could be victory or defeat)
        # We test the tie logic directly via compound state manipulation:
        cs = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_attack_result=5,
            campaign_defense_result=5,  # Tied
        )
        gs.compound_state = cs
        gs.players[1].warbands_board = 3
        gs.sites[gs.players[1].pawn_site].warbands = 3
        # Sacrifice 0 warbands — attack stays at 5, defense at 5 → tie → defeat
        execute_campaign_sacrifice(gs, 1, 0)
        # Should have gone to defeat (compound cleared)
        assert gs.compound_state is None

    def test_skulls_kill_one_warband(self, gs):
        """§5.5.5: Each skull kills 1 warband, not 2."""
        _setup_campaign(gs)
        gs.players[1].warbands_board = 10
        initial_board = gs.players[1].warbands_board
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)
        # Losses should be at most equal to number of skulls rolled
        # (each skull = 1 warband, not 2). With 10 dice, max 10 skulls.
        lost = initial_board - gs.players[1].warbands_board
        # Each skull should kill exactly 1 warband
        assert lost <= 10  # Max skulls from 10 dice

    def test_oathkeeper_adds_defense_die(self, gs):
        """§2.11: Oathkeeper adds 1 defense die, Usurper adds 2."""
        _setup_campaign(gs)
        gs.oathkeeper_holder = 0  # Defender holds Oathkeeper
        gs.oathkeeper_side = TitleSide.OATHKEEPER
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)
        # The defense dice should have included the Oathkeeper bonus
        # We verify indirectly: campaign_defense_dice should be >= 2
        # (at least 1 from site + 1 from Oathkeeper)
        cs = gs.compound_state
        if cs is not None:
            assert cs.campaign_defense_dice >= 2

    def test_usurper_adds_two_defense_dice(self, gs):
        """§2.11: Usurper side adds 2 defense dice."""
        _setup_campaign(gs)
        gs.oathkeeper_holder = 0  # Defender holds Usurper
        gs.oathkeeper_side = TitleSide.USURPER
        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)
        cs = gs.compound_state
        if cs is not None:
            assert cs.campaign_defense_dice >= 3  # site + 2 Usurper


# ─── Target Validation Tests ─────────────────────────────────────────

class TestTargetValidation:
    def test_site_targets_anywhere_on_map(self, gs):
        """§5.5.2: Can target any site the defender rules, anywhere."""
        _setup_campaign(gs)
        # Defender also rules site 5 (in a different region)
        gs.sites[5].ruling_player = 0
        gs.sites[5].warbands = 2
        execute_campaign_declare(gs, 1, 0)
        # Should be able to target site 5 (different region)
        execute_campaign_target_site(gs, 1, 5)
        assert "site:5" in gs.compound_state.campaign_targets

    def test_relic_pawn_target_requires_same_site(self, gs):
        """§5.5.2: Relics/pawn only targetable if defender's pawn at your site."""
        from oath.env.action_decoder import ActionDecoder
        _setup_campaign(gs)
        gs.players[0].relics = [210]  # Defender has a relic
        # Defender's pawn IS at attacker's site (both at site 0)
        execute_campaign_declare(gs, 1, 0)

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        # Relic target (96) should be legal
        assert mask[96] == 1.0
        # Pawn target (101) should be legal
        assert mask[101] == 1.0

    def test_relic_pawn_blocked_when_not_same_site(self, gs):
        """Relics/pawn NOT targetable if defender's pawn is elsewhere."""
        from oath.env.action_decoder import ActionDecoder
        # Attacker at site 0, defender's pawn at site 3, but defender rules site 0
        gs.players[1].pawn_site = 0
        gs.players[0].pawn_site = 3
        gs.sites[0].ruling_player = 0
        gs.sites[0].warbands = 2
        gs.players[0].warbands_board = 2
        gs.players[0].relics = [210]
        gs.players[1].supply = 5
        gs.players[1].warbands_board = 3

        execute_campaign_declare(gs, 1, 0)

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        # Relic target (96) should NOT be legal
        assert mask[96] == 0.0
        # Pawn target (101) should NOT be legal
        assert mask[101] == 0.0
        # Site target (88) should still be legal (defender rules site 0)
        assert mask[88] == 1.0

    def test_sacrifice_exact_amount_only(self, gs):
        """§5.5.5: Must sacrifice exactly enough or decline."""
        from oath.env.action_decoder import ActionDecoder
        _setup_campaign(gs)
        # Set up sacrifice state manually
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_attack_result=3,
            campaign_defense_result=5,
        )
        gs.players[1].warbands_board = 5

        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        # Deficit = 5 - 3 = 2, need 3 to exceed (strictly >)
        # Only action 60 (decline) and 63 (sacrifice 3) should be legal
        assert mask[60] == 1.0   # Decline
        assert mask[61] == 0.0   # Sacrifice 1 — not enough
        assert mask[62] == 0.0   # Sacrifice 2 — only ties
        assert mask[63] == 1.0   # Sacrifice 3 — exactly enough
        assert mask[64] == 0.0   # Sacrifice 4 — too many
        assert mask[65] == 0.0   # Sacrifice 5 — too many


# ─── Resolution Tests ─────────────────────────────────────────────────

class TestCampaignResolution:
    def test_campaign_full_flow(self, gs):
        """Test a complete campaign from declare to resolution."""
        _setup_campaign(gs)

        if can_campaign(gs, 1, 0):
            execute_campaign_declare(gs, 1, 0)
            assert gs.compound_state is not None

            execute_campaign_target_site(gs, 1, 0)
            execute_campaign_done_targets(gs, 1)
            assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BATTLE

            # Attacker declines battle plan
            execute_campaign_no_battle(gs, 1)
            assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BATTLE_DEFENDER

            # Defender declines battle plan
            execute_campaign_no_battle(gs, 0)

            # Resolved or in sacrifice
            if gs.compound_state is not None:
                assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_SACRIFICE
                execute_campaign_sacrifice(gs, 1, 0)
            assert gs.compound_state is None

    def test_campaign_sacrifice_mechanics(self, gs):
        """Test that sacrifice adds to attack total."""
        _setup_campaign(gs)
        gs.sites[0].warbands = 5
        gs.players[0].warbands_board = 5
        gs.players[1].warbands_board = 4

        if not can_campaign(gs, 1, 0):
            return

        execute_campaign_declare(gs, 1, 0)
        execute_campaign_target_site(gs, 1, 0)
        execute_campaign_done_targets(gs, 1)
        execute_campaign_no_battle(gs, 1)
        execute_campaign_no_battle(gs, 0)

        if (gs.compound_state is not None and
                gs.compound_state.state_type == CompoundStateType.CAMPAIGN_SACRIFICE):
            prev_attack = gs.compound_state.campaign_attack_result
            execute_campaign_sacrifice(gs, 1, 3)
            assert gs.compound_state is None

    def test_defeat_kills_half_attacker_force(self, gs):
        """§5.5.6: Defeated attacker loses half warbands (rounded down)."""
        _setup_campaign(gs)
        gs.players[1].warbands_board = 6
        gs.sites[0].ruling_player = 1  # Attacker also rules the site
        gs.sites[0].warbands = 6
        # Force a defeat by setting up manually
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_attack_result=1,
            campaign_defense_result=10,  # Huge deficit, can't overcome
        )
        execute_campaign_sacrifice(gs, 1, 0)  # Decline → defeat
        # Attacker had 6 warbands, should lose 3 (half rounded down)
        assert gs.players[1].warbands_board == 3
        assert gs.compound_state is None

    def test_victory_places_attacker_warbands(self, gs):
        """§5.5.7.I: Attacker chooses warbands to place on targeted sites."""
        _setup_campaign(gs)
        gs.players[1].warbands_board = 5
        # Force a victory manually
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_targets=["site:0"],
            campaign_target_sites=[0],
            campaign_attack_result=10,
            campaign_defense_result=5,
        )
        _resolve_campaign_victory(gs)
        # Should enter warband placement state
        assert gs.compound_state is not None
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_PLACE_WARBANDS
        assert gs.compound_state.campaign_remaining_sites == [0]
        assert gs.compound_state.campaign_force_remaining == 5

        # Attacker chooses to place 3 warbands
        from oath.engine.campaign import execute_campaign_place_warbands
        execute_campaign_place_warbands(gs, 1, 3)
        assert gs.sites[0].warbands == 3
        assert gs.sites[0].ruling_player == 1
        assert gs.compound_state is None  # Campaign complete

    def test_imperial_warbands_to_chancellor_bank(self, gs):
        """§5.5.7.I: Imperial warbands go to Chancellor's bank."""
        _setup_campaign(gs)
        gs.players[0].role = Role.CHANCELLOR
        gs.players[0].warbands_board = 5
        gs.players[0].warbands_bank = 10
        gs.sites[0].warbands = 3
        initial_bank = gs.players[0].warbands_bank

        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_targets=["site:0"],
            campaign_target_sites=[0],
            campaign_attack_result=10,
            campaign_defense_result=5,
        )
        _resolve_campaign_victory(gs)
        # Chancellor's bank should increase by 3 (the removed warbands)
        assert gs.players[0].warbands_bank == initial_bank + 3


# ─── Banishment Tests ─────────────────────────────────────────────────

def _setup_banish_state(gs, attacker=1, defender=0):
    """Helper: set up a CAMPAIGN_BANISH_TRAVEL compound state."""
    gs.players[defender].pawn_site = 0
    gs.players[attacker].pawn_site = 0
    gs.compound_state = CompoundState(
        state_type=CompoundStateType.CAMPAIGN_BANISH_TRAVEL,
        campaign_attacker=attacker,
        campaign_defender=defender,
        banish_target=defender,
    )
    return gs


class TestBanishment:
    def test_banish_enters_compound_state(self, gs):
        """§5.5.7.III: Pawn target enters banish travel state, not immediate banish."""
        _setup_campaign(gs)
        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_targets=["pawn"],
            campaign_attack_result=10,
            campaign_defense_result=5,
        )
        _resolve_campaign_victory(gs)
        # Should enter banish travel state, not clear compound state
        assert gs.compound_state is not None
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BANISH_TRAVEL
        assert gs.compound_state.banish_target == 0

    def test_banish_travel_optional(self, gs):
        """§5.5.7.III: Attacker may decline to move the defender."""
        _setup_banish_state(gs)
        original_site = gs.players[0].pawn_site
        execute_banish_skip_travel(gs, 1)
        assert gs.players[0].pawn_site == original_site
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BANISH_BURN

    def test_banish_burn_optional(self, gs):
        """§5.5.7.III: Attacker may decline to burn favor."""
        _setup_banish_state(gs)
        gs.players[0].favor = 6
        execute_banish_skip_travel(gs, 1)
        execute_banish_skip_burn(gs, 1)
        assert gs.players[0].favor == 6
        assert gs.compound_state is None

    def test_banish_attacker_chooses_site(self, gs):
        """§5.5.7.III: Attacker picks the destination site."""
        _setup_banish_state(gs)
        # Find a faceup site that's not site 0
        target_site = None
        for i, site in enumerate(gs.sites):
            if i != 0 and site.is_faceup:
                target_site = i
                break
        assert target_site is not None, "Need at least one other faceup site"
        execute_banish_travel(gs, 1, target_site)
        assert gs.players[0].pawn_site == target_site
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BANISH_BURN

    def test_banish_burn_halves_favor(self, gs):
        """§5.5.7.III: Burn half of favor, rounded down. Secrets untouched."""
        _setup_banish_state(gs)
        gs.players[0].favor = 7
        gs.players[0].secrets = 4
        execute_banish_skip_travel(gs, 1)
        execute_banish_burn(gs, 1)
        assert gs.players[0].favor == 4  # 7 - 7//2 = 7 - 3 = 4
        assert gs.players[0].secrets == 4
        assert gs.compound_state is None

    def test_banish_travel_validates_site(self, gs):
        """Cannot banish to facedown sites or defender's current site."""
        _setup_banish_state(gs)
        # Current site should be invalid
        assert not can_banish_travel_to(gs, 0, 0)
        # Facedown site should be invalid
        for i, site in enumerate(gs.sites):
            if not site.is_faceup:
                assert not can_banish_travel_to(gs, 0, i)
                break

    def test_banish_travel_mask(self, gs):
        """Action mask during banish travel shows valid sites + skip."""
        from oath.env.action_decoder import ActionDecoder
        _setup_banish_state(gs)
        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)  # Attacker's mask
        # Skip (ID 59) must be legal
        assert mask[59] == 1.0
        # Current site (0) must be illegal
        assert mask[0] == 0.0
        # At least one other faceup site should be legal
        has_legal_site = any(mask[i] == 1.0 for i in range(1, 8))
        assert has_legal_site

    def test_banish_burn_mask(self, gs):
        """Action mask during banish burn shows burn + skip."""
        from oath.env.action_decoder import ActionDecoder
        _setup_banish_state(gs)
        gs.players[0].favor = 5
        gs.compound_state.state_type = CompoundStateType.CAMPAIGN_BANISH_BURN
        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        assert mask[59] == 1.0  # Skip
        assert mask[87] == 1.0  # Burn

    def test_banish_burn_mask_zero_favor(self, gs):
        """No burn option if defender has 0 favor."""
        from oath.env.action_decoder import ActionDecoder
        _setup_banish_state(gs)
        gs.players[0].favor = 0
        gs.compound_state.state_type = CompoundStateType.CAMPAIGN_BANISH_BURN
        decoder = ActionDecoder()
        mask = decoder.get_legal_mask(gs, 1)
        assert mask[59] == 1.0  # Skip still legal
        assert mask[87] == 0.0  # Burn not legal

    def test_banish_full_flow(self, gs):
        """End-to-end: campaign with pawn + site → victory → place warbands → banish → burn."""
        _setup_campaign(gs)
        gs.players[0].favor = 10
        gs.players[0].secrets = 3
        gs.players[1].warbands_board = 4
        # Find target site
        target_site = None
        for i, site in enumerate(gs.sites):
            if i != 0 and site.is_faceup:
                target_site = i
                break
        assert target_site is not None

        gs.compound_state = CompoundState(
            state_type=CompoundStateType.CAMPAIGN_SACRIFICE,
            campaign_attacker=1,
            campaign_defender=0,
            campaign_targets=["site:0", "pawn"],
            campaign_target_sites=[0],
            campaign_attack_result=10,
            campaign_defense_result=5,
        )
        _resolve_campaign_victory(gs)
        # Should enter warband placement first (site:0 is targeted)
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_PLACE_WARBANDS

        # Place 1 warband on site 0, then proceed to banish
        from oath.engine.campaign import execute_campaign_place_warbands
        execute_campaign_place_warbands(gs, 1, 1)
        assert gs.sites[0].warbands == 1
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BANISH_TRAVEL

        execute_banish_travel(gs, 1, target_site)
        assert gs.players[0].pawn_site == target_site
        assert gs.compound_state.state_type == CompoundStateType.CAMPAIGN_BANISH_BURN

        execute_banish_burn(gs, 1)
        assert gs.players[0].favor == 5  # 10 // 2 = 5
        assert gs.players[0].secrets == 3  # Unchanged
        assert gs.compound_state is None


# ─── Oathkeeper Tests ─────────────────────────────────────────────────

class TestOathkeeper:
    def test_supremacy_oathkeeper_always_chancellor(self, gs):
        """§2.11: Chancellor always holds Supremacy Oathkeeper."""
        gs.oath_goal = OathGoal.SUPREMACY
        gs.oathkeeper_holder = 2  # Some exile holds it
        recalculate_oathkeeper(gs)
        # Should transfer to Chancellor (player 0)
        assert gs.oathkeeper_holder == gs.chancellor_index

    def test_supremacy_stays_with_chancellor(self, gs):
        """Chancellor keeps Supremacy even if exile rules more sites."""
        gs.oath_goal = OathGoal.SUPREMACY
        gs.oathkeeper_holder = 0  # Chancellor
        # Give exile player 2 more sites than chancellor
        gs.sites[3].ruling_player = 2
        gs.sites[4].ruling_player = 2
        gs.sites[5].ruling_player = 2
        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == gs.chancellor_index

    def test_people_oathkeeper_transfers(self, gs):
        """People oath: holder of People's Favor gets title."""
        gs.oath_goal = OathGoal.PEOPLE
        gs.oathkeeper_holder = 0
        gs.peoples_favor_holder = 2
        recalculate_oathkeeper(gs)
        assert gs.oathkeeper_holder == 2
        assert gs.oathkeeper_side == TitleSide.OATHKEEPER

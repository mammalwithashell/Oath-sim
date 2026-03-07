"""Tests for the chronicle system (Section 8 of Law of Oath)."""

import pytest
import numpy as np

from oath.enums import (
    OathGoal, SuccessorGoal, Role, Suit, Region, TitleSide, ActionType,
    SUIT_CLOCKWISE_ORDER, OATH_TO_SUCCESSOR, VISION_TO_OATH_GOAL,
)
from oath.state.game_state import GameState
from oath.state.player_state import PlayerState
from oath.state.site_state import SiteState
from oath.state.chronicle_state import ChronicleState, ChronicleSiteSnapshot
from oath.engine.chronicle import (
    apply_chronicle, _vow_an_oath, _offer_citizenship,
    _add_cards_to_world_deck, _remove_cards_to_dispossessed,
    _rebuild_world_deck, _initialize_archive, _heal_archive,
)
from oath.engine.game import create_initial_state
from oath.cards.database import get_card, get_vision_ids, get_edifice_ids


def _make_finished_game(seed=42, winner=0, vision_id=None) -> GameState:
    """Create a completed game state for testing chronicle."""
    gs = create_initial_state(num_players=4, seed=seed)
    gs.is_game_over = True
    gs.winner = winner
    gs.round_number = 6

    if vision_id is not None:
        gs.players[winner].revealed_vision = vision_id

    # Give winner some advisers
    gs.players[winner].advisers[0] = 1  # Longbows (ORDER)
    gs.players[winner].adviser_faceup[0] = True
    gs.players[winner].advisers[1] = 2  # Taming Charm (ARCANE)
    gs.players[winner].adviser_faceup[1] = True

    return gs


class TestVowAnOath:
    def test_vision_win_sets_matching_goal(self):
        """8.1: Vision win → oath goal matches the vision."""
        gs = _make_finished_game(winner=1, vision_id=221)  # Conquest
        goal = _vow_an_oath(gs, winner=1)
        assert goal == OathGoal.SUPREMACY

    def test_vision_of_faith_sets_devotion(self):
        gs = _make_finished_game(winner=1, vision_id=222)
        goal = _vow_an_oath(gs, winner=1)
        assert goal == OathGoal.DEVOTION

    def test_vision_of_rebellion_sets_people(self):
        gs = _make_finished_game(winner=1, vision_id=223)
        goal = _vow_an_oath(gs, winner=1)
        assert goal == OathGoal.PEOPLE

    def test_vision_of_sanctuary_sets_sanctuary(self):
        gs = _make_finished_game(winner=1, vision_id=224)
        goal = _vow_an_oath(gs, winner=1)
        assert goal == OathGoal.SANCTUARY

    def test_non_vision_win_chooses_different_goal(self):
        """8.1: Non-vision win → any goal except current."""
        gs = _make_finished_game(winner=0)
        gs.oath_goal = OathGoal.SUPREMACY
        goal = _vow_an_oath(gs, winner=0)
        assert goal != OathGoal.SUPREMACY

    def test_callback_overrides_heuristic(self):
        gs = _make_finished_game(winner=0)
        gs.oath_goal = OathGoal.SUPREMACY
        goal = _vow_an_oath(
            gs, winner=0,
            callback=lambda gs, avail: OathGoal.DEVOTION,
        )
        assert goal == OathGoal.DEVOTION


class TestOfferCitizenship:
    def test_exile_winner_flips_citizens_to_exile(self):
        """8.2: Exile winner flips all Citizens to Exile first."""
        gs = _make_finished_game(winner=1)
        gs.players[1].role = Role.EXILE
        gs.players[2].role = Role.CITIZEN
        gs.players[3].role = Role.EXILE

        boards = _offer_citizenship(gs, winner=1)
        # Player 2 (index 1 in boards) was Citizen → flipped to Exile
        assert boards[1] == Role.EXILE

    def test_callback_controls_acceptance(self):
        gs = _make_finished_game(winner=1)
        gs.players[1].role = Role.EXILE

        # Always accept
        boards = _offer_citizenship(
            gs, winner=1,
            callback=lambda pi, gs: True,
        )
        # All non-winner Exiles should become Citizens
        for i, role in enumerate(boards):
            if i + 1 != 1:  # skip winner
                assert role == Role.CITIZEN


class TestAddCardsToWorldDeck:
    def test_adds_six_cards_from_archive(self):
        """8.4: Should add 6 cards in 3/2/1 distribution."""
        gs = _make_finished_game(winner=0)
        chronicle = ChronicleState()
        _initialize_archive(chronicle, gs)

        initial_deck_size = len(gs.world_deck)
        rng = np.random.default_rng(42)
        _add_cards_to_world_deck(gs, chronicle, winner=0, rng=rng)

        added = len(gs.world_deck) - initial_deck_size
        assert added == 6

    def test_uses_winner_adviser_suits(self):
        """8.4: Primary suit comes from winner's advisers."""
        gs = _make_finished_game(winner=0)
        # Give winner 2 ORDER advisers
        gs.players[0].advisers = [1, 17, None]  # Longbows, Wrestlers (both ORDER)
        gs.players[0].adviser_faceup = [True, True, False]

        chronicle = ChronicleState()
        _initialize_archive(chronicle, gs)
        rng = np.random.default_rng(42)

        order_before = sum(
            1 for cid in gs.world_deck if get_card(cid).suit == Suit.ORDER
        )
        _add_cards_to_world_deck(gs, chronicle, winner=0, rng=rng)
        order_after = sum(
            1 for cid in gs.world_deck if get_card(cid).suit == Suit.ORDER
        )

        # Should have added at least 3 ORDER cards
        assert order_after - order_before >= 3


class TestRemoveCardsToDispossessed:
    def test_removes_six_cards(self):
        """8.5: Should remove exactly 6 non-vision cards."""
        gs = _make_finished_game(winner=0)
        # Put some cards in discard
        gs.discard_piles[0] = [20, 21, 22, 23, 24, 25, 26, 27]

        chronicle = ChronicleState()
        rng = np.random.default_rng(42)
        _remove_cards_to_dispossessed(gs, chronicle, winner=0, rng=rng)

        total_dispossessed = sum(len(v) for v in chronicle.dispossessed.values())
        assert total_dispossessed == 6

    def test_excludes_visions(self):
        """8.5: Vision cards should NOT be removed."""
        gs = _make_finished_game(winner=0)
        vision_ids = set(get_vision_ids())
        gs.discard_piles[0] = [221, 222, 20, 21, 22, 23, 24, 25, 26, 27]

        chronicle = ChronicleState()
        rng = np.random.default_rng(42)
        _remove_cards_to_dispossessed(gs, chronicle, winner=0, rng=rng)

        # No visions in dispossessed
        for cards in chronicle.dispossessed.values():
            for cid in cards:
                assert cid not in vision_ids


class TestRebuildWorldDeck:
    def test_vision_layering(self):
        """8.8: Visions should be in top 12 (2) and next 18 (3) cards."""
        gs = _make_finished_game(winner=0)
        chronicle = ChronicleState()
        rng = np.random.default_rng(42)

        _rebuild_world_deck(gs, chronicle, rng)

        deck = chronicle.world_deck
        vision_ids = set(get_vision_ids())

        # Count visions in top 12
        top_12 = deck[:12]
        visions_top = sum(1 for c in top_12 if c in vision_ids)

        # Count visions in next 18
        mid_18 = deck[12:30]
        visions_mid = sum(1 for c in mid_18 if c in vision_ids)

        assert visions_top == 2, f"Expected 2 visions in top 12, got {visions_top}"
        assert visions_mid == 3, f"Expected 3 visions in middle 18, got {visions_mid}"

    def test_no_duplicate_cards(self):
        """Cards should not appear twice in the rebuilt deck."""
        gs = _make_finished_game(winner=0)
        chronicle = ChronicleState()
        rng = np.random.default_rng(42)

        _rebuild_world_deck(gs, chronicle, rng)

        seen = set()
        for cid in chronicle.world_deck:
            assert cid not in seen, f"Duplicate card {cid} in world deck"
            seen.add(cid)


class TestArchiveHeal:
    def test_heal_moves_dispossessed_to_archive(self):
        """Healing should transfer cards from Dispossessed to Archive."""
        chronicle = ChronicleState()
        chronicle.dispossessed = {
            0: [23, 24],  # DISCORD
            1: [37, 38],  # ARCANE
            2: [], 3: [], 4: [], 5: [],
        }
        chronicle.archive = {s: [] for s in range(6)}

        rng = np.random.default_rng(42)
        _heal_archive(chronicle, rng)

        assert len(chronicle.archive[0]) == 2
        assert len(chronicle.archive[1]) == 2
        assert len(chronicle.dispossessed[0]) == 0
        assert len(chronicle.dispossessed[1]) == 0


class TestFullChronicle:
    def test_chronicle_produces_valid_state(self):
        """Full chronicle should produce a valid ChronicleState."""
        gs = _make_finished_game(winner=0)
        chronicle = apply_chronicle(gs)

        assert chronicle.games_played == 1
        assert chronicle.last_winner == 0
        assert chronicle.oath_goal in list(OathGoal)
        assert chronicle.successor_goal in list(SuccessorGoal)
        assert len(chronicle.world_deck) > 0

    def test_chronicle_chain(self):
        """Can chain 3 games through chronicle without errors."""
        gs1 = _make_finished_game(seed=42, winner=0)
        c1 = apply_chronicle(gs1)
        assert c1.games_played == 1

        gs2 = create_initial_state(num_players=4, seed=43, chronicle=c1)
        gs2.is_game_over = True
        gs2.winner = 1
        gs2.players[1].revealed_vision = 221
        c2 = apply_chronicle(gs2, prev_chronicle=c1)
        assert c2.games_played == 2

        gs3 = create_initial_state(num_players=4, seed=44, chronicle=c2)
        gs3.is_game_over = True
        gs3.winner = 2
        c3 = apply_chronicle(gs3, prev_chronicle=c2)
        assert c3.games_played == 3

    def test_chronicle_env_integration(self):
        """OathEnv in chronicle mode should chain games on reset."""
        from oath.env.oath_env import OathEnv

        env = OathEnv(num_players=4, seed=42, chronicle_mode=True)
        env.reset()

        # Play a quick game (random actions)
        for agent in env.agent_iter(max_iter=3000):
            obs, reward, terminated, truncated, info = env.last()
            if terminated or truncated:
                action = None
            else:
                mask = obs["action_mask"]
                legal = np.where(mask > 0.5)[0]
                action = int(np.random.choice(legal)) if len(legal) > 0 else None
            env.step(action)
            if env.game_state and env.game_state.is_game_over:
                break

        # Reset should apply chronicle
        env.reset(seed=43)
        assert env._chronicle_state is not None
        assert env._chronicle_state.games_played == 1


class TestCitizenshipRewards:
    def test_exile_vision_reward(self):
        """Exile should get extra reward for revealing a vision."""
        from oath.env.reward import compute_reward
        from oath.env.action_decoder import DecodedAction

        prev = create_initial_state(num_players=4, seed=42)
        new = create_initial_state(num_players=4, seed=42)
        new.players[1].revealed_vision = 221
        new.players[1].role = Role.EXILE
        prev.players[1].role = Role.EXILE

        action = DecodedAction(action_type=ActionType.END_ACT_PHASE)
        reward = compute_reward(prev, action, new, player_idx=1)
        # Should include vision reveal bonus (at least 2.0 * 0.01 = 0.02)
        assert reward >= 0.02

    def test_citizen_successor_reward(self):
        """Citizen should get reward for closing gap on successor goal."""
        from oath.env.reward import compute_reward
        from oath.env.action_decoder import DecodedAction

        prev = create_initial_state(num_players=4, seed=42)
        new = create_initial_state(num_players=4, seed=42)

        # Make player 1 a Citizen
        prev.players[1].role = Role.CITIZEN
        new.players[1].role = Role.CITIZEN
        prev.successor_goal = SuccessorGoal.MOST_SITES
        new.successor_goal = SuccessorGoal.MOST_SITES

        # Player 1 gains a faceup site, Chancellor doesn't
        new.sites[3].ruling_player = 1
        new.sites[3].is_faceup = True

        action = DecodedAction(action_type=ActionType.END_ACT_PHASE)
        reward = compute_reward(prev, action, new, player_idx=1)
        # Should include site gain reward + citizen gap-closing reward
        assert reward > 0

    def test_chancellor_threat_penalty(self):
        """Chancellor should get penalty when Exile reveals a vision."""
        from oath.env.reward import compute_reward
        from oath.env.action_decoder import DecodedAction

        prev = create_initial_state(num_players=4, seed=42)
        new = create_initial_state(num_players=4, seed=42)

        # Exile reveals vision
        new.players[1].revealed_vision = 221
        new.players[1].role = Role.EXILE
        prev.players[1].role = Role.EXILE

        action = DecodedAction(action_type=ActionType.END_ACT_PHASE)
        reward = compute_reward(prev, action, new, player_idx=0)  # Chancellor
        # Should include a threat penalty
        assert reward < 0

    def test_citizenship_acceptance_reward(self):
        """Accepting citizenship when meeting successor goal gives bonus."""
        from oath.env.reward import compute_reward
        from oath.env.action_decoder import DecodedAction

        prev = create_initial_state(num_players=4, seed=42)
        new = create_initial_state(num_players=4, seed=42)

        prev.players[1].role = Role.EXILE
        new.players[1].role = Role.CITIZEN
        new.successor_goal = SuccessorGoal.MOST_SITES

        # Player 1 rules more faceup sites than Chancellor
        new.sites[2].ruling_player = 1
        new.sites[2].is_faceup = True
        new.sites[3].ruling_player = 1
        new.sites[3].is_faceup = True
        new.sites[4].ruling_player = 1
        new.sites[4].is_faceup = True

        action = DecodedAction(action_type=ActionType.END_ACT_PHASE)
        reward = compute_reward(prev, action, new, player_idx=1)
        assert reward > 0


class TestChronicleObservation:
    def test_observation_size(self):
        """Chronicle citizenship observation should have correct size."""
        from oath.env.observation import (
            encode_chronicle_citizenship_observation, CHRONICLE_OBS_SIZE,
        )

        gs = create_initial_state(num_players=4, seed=42)
        obs = encode_chronicle_citizenship_observation(
            gs, player_index=1,
            new_oath_goal=int(OathGoal.DEVOTION),
            new_successor_goal=int(SuccessorGoal.DARKEST_SECRET),
        )

        assert obs.shape == (CHRONICLE_OBS_SIZE,)
        assert obs.dtype == np.float32

    def test_oath_goal_encoded(self):
        """Should correctly encode the new oath goal as one-hot."""
        from oath.env.observation import encode_chronicle_citizenship_observation

        gs = create_initial_state(num_players=4, seed=42)
        obs = encode_chronicle_citizenship_observation(
            gs, player_index=1,
            new_oath_goal=int(OathGoal.DEVOTION),
            new_successor_goal=int(SuccessorGoal.DARKEST_SECRET),
        )

        # Oath goal one-hot: positions 0-3
        assert obs[int(OathGoal.DEVOTION)] == 1.0
        assert obs[int(OathGoal.SUPREMACY)] == 0.0

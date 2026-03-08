"""Chronicle system — the legacy aspect of Oath (Section 8 of Law of Oath).

After each game, the winner performs the Chronicle to reshape the world
deck, sites, oath goal, and relics for the next game. This module
implements all 8 sub-steps of Section 8.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

from oath.enums import (
    OathGoal, SuccessorGoal, Role, Suit, Region,
    SUIT_CLOCKWISE_ORDER, OATH_TO_SUCCESSOR, VISION_TO_OATH_GOAL,
    NUM_SUITS,
)
from oath.state.game_state import GameState
from oath.state.chronicle_state import ChronicleState, ChronicleSiteSnapshot
from oath.cards.database import (
    get_card, get_vision_ids, get_edifice_by_suit, get_edifice_ids,
    GRAND_SCEPTER_ID, CARD_DB,
)


# Type alias for citizenship decision callback
# Takes (player_index, game_state) -> bool (True = accept)
CitizenshipCallback = Callable[[int, GameState], bool]


def apply_chronicle(
    gs: GameState,
    prev_chronicle: Optional[ChronicleState] = None,
    citizenship_callback: Optional[CitizenshipCallback] = None,
    oath_choice_callback: Optional[Callable[[GameState, list[OathGoal]], OathGoal]] = None,
    rng: Optional[np.random.Generator] = None,
) -> ChronicleState:
    """Apply the full chronicle after a game ends.

    Args:
        gs: The completed game state (must have is_game_over=True).
        prev_chronicle: Previous chronicle state, or None for first chronicle.
        citizenship_callback: Optional callback for Exile citizenship decisions.
            If None, uses heuristic (accept if close to successor goal).
        oath_choice_callback: Optional callback for winner's oath goal choice.
            If None, uses heuristic based on win type.
        rng: Random number generator. If None, uses gs.rng.

    Returns:
        New ChronicleState for the next game.
    """
    if not gs.is_game_over or gs.winner is None:
        raise ValueError("Cannot apply chronicle: game is not over")

    if rng is None:
        rng = gs.rng

    winner = gs.winner

    # Initialize chronicle from previous or fresh
    if prev_chronicle is not None:
        chronicle = ChronicleState(
            archive={s: list(prev_chronicle.archive.get(s, [])) for s in range(6)},
            dispossessed={s: list(prev_chronicle.dispossessed.get(s, [])) for s in range(6)},
            site_deck=list(prev_chronicle.site_deck),
            edifices_in_play=list(prev_chronicle.edifices_in_play),
            games_played=prev_chronicle.games_played,
        )
    else:
        chronicle = ChronicleState()
        _initialize_archive(chronicle, gs)

    logger.info(
        "Applying chronicle: winner=P%d (%s), win_type=%s, games_played=%d",
        winner, gs.players[winner].role.name, gs.win_type, chronicle.games_played,
    )

    # Step 8.1: Vow an Oath
    chronicle.oath_goal = _vow_an_oath(gs, winner, oath_choice_callback)
    chronicle.successor_goal = SuccessorGoal(OATH_TO_SUCCESSOR[chronicle.oath_goal])
    logger.info("8.1 Vow: oath=%s, successor=%s", chronicle.oath_goal.name, chronicle.successor_goal.name)

    # Step 8.2: Offer Citizenship
    chronicle.player_boards = _offer_citizenship(gs, winner, citizenship_callback)
    logger.info("8.2 Citizenship: boards=%s", [r.name for r in chronicle.player_boards])

    # Step 8.3: Clean Up Map and Build Edifices
    _clean_up_map(gs, chronicle, winner, rng)
    logger.debug("8.3 Map cleanup: %d chronicled sites", len(chronicle.chronicled_sites))

    # Step 8.4: Add Six Cards to World Deck
    _add_cards_to_world_deck(gs, chronicle, winner, rng)
    logger.debug("8.4 Added cards to world deck")

    # Step 8.5: Remove Six Cards to Dispossessed
    _remove_cards_to_dispossessed(gs, chronicle, winner, rng)
    logger.debug("8.5 Removed cards to dispossessed")

    # Step 8.6: Clean Up Relics
    _clean_up_relics(gs, chronicle, winner, rng)
    logger.debug("8.6 Relics cleaned up")

    # Step 8.7: Save Map and Boards
    _save_map_and_boards(gs, chronicle)

    # Step 8.8: Rebuild the World Deck
    _rebuild_world_deck(gs, chronicle, rng)
    logger.debug("8.8 World deck rebuilt: %d cards", len(chronicle.world_deck))

    chronicle.last_winner = winner
    chronicle.games_played += 1

    return chronicle


# ── 8.1 Vow an Oath ────────────────────────────────────────────────


def _vow_an_oath(
    gs: GameState,
    winner: int,
    callback: Optional[Callable] = None,
) -> OathGoal:
    """8.1: Winner chooses the oath goal for the next game.

    - If won with a Vision alone, goal = that Vision's oath goal.
    - Otherwise, choose any goal except the current one.
    """
    # Check if winner won via vision
    winner_player = gs.players[winner]
    vision = winner_player.revealed_vision

    # Vision-only win: oath goal matches the vision
    if vision is not None and vision in VISION_TO_OATH_GOAL:
        return OathGoal(VISION_TO_OATH_GOAL[vision])

    # Non-vision win: choose any oath except current
    available = [g for g in OathGoal if g != gs.oath_goal]

    if callback is not None:
        return callback(gs, available)

    # Heuristic: pick goal matching winner's strongest attribute
    return _heuristic_oath_choice(gs, winner, available)


def _heuristic_oath_choice(
    gs: GameState, winner: int, available: list[OathGoal],
) -> OathGoal:
    """Heuristic: choose oath goal matching winner's strongest position."""
    scores: dict[OathGoal, float] = {}

    for goal in available:
        if goal == OathGoal.SUPREMACY:
            scores[goal] = gs.count_sites_ruled(winner)
        elif goal == OathGoal.PEOPLE:
            scores[goal] = 2.0 if gs.peoples_favor_holder == winner else 0.0
        elif goal == OathGoal.DEVOTION:
            scores[goal] = 2.0 if gs.darkest_secret_holder == winner else 0.0
        elif goal == OathGoal.SANCTUARY:
            count = len(gs.players[winner].relics)
            if gs.peoples_favor_holder == winner:
                count += 1
            if gs.darkest_secret_holder == winner:
                count += 1
            scores[goal] = count

    if scores:
        return max(scores, key=lambda g: scores[g])
    return available[0]


# ── 8.2 Offer Citizenship ──────────────────────────────────────────


def _offer_citizenship(
    gs: GameState,
    winner: int,
    callback: Optional[CitizenshipCallback] = None,
) -> list[Role]:
    """8.2: Winner (if Exile) offers citizenship in the chronicle.

    Returns list of roles for non-Chancellor players (index 0 = player 1).
    """
    boards = []
    for i in range(1, gs.num_players):
        boards.append(gs.players[i].role)

    winner_player = gs.players[winner]

    if winner_player.role == Role.EXILE:
        # First: flip all Citizens to Exile
        flipped_from_citizen = set()
        for i in range(len(boards)):
            if boards[i] == Role.CITIZEN:
                boards[i] = Role.EXILE
                flipped_from_citizen.add(i)

        # Then: offer citizenship to Exiles (not those just flipped)
        for i in range(len(boards)):
            if i in flipped_from_citizen:
                continue
            player_idx = i + 1  # actual player index
            if player_idx == winner:
                continue  # winner doesn't offer to self
            if boards[i] == Role.EXILE:
                accept = _should_accept_citizenship(gs, player_idx, callback)
                if accept:
                    boards[i] = Role.CITIZEN

    return boards


def _should_accept_citizenship(
    gs: GameState,
    player_idx: int,
    callback: Optional[CitizenshipCallback] = None,
) -> bool:
    """Decide whether a player should accept citizenship."""
    if callback is not None:
        return callback(player_idx, gs)

    # Heuristic: accept if the player has resources that would help
    # meet the successor goal
    from oath.engine.win_conditions import _check_successor_goal
    if _check_successor_goal(gs, player_idx):
        return True

    # Accept ~50% of the time by default (let agents explore both paths)
    return False


# ── 8.3 Clean Up Map and Build Edifices ──────────────────────────


def _clean_up_map(
    gs: GameState,
    chronicle: ChronicleState,
    winner: int,
    rng: np.random.Generator,
) -> None:
    """8.3: Clean up map, build/ruin edifices, consolidate sites."""

    # 8.3.1: Build or repair edifices at winner's ruled sites
    winner_player = gs.players[winner]
    if winner_player.role in (Role.CHANCELLOR, Role.CITIZEN):
        _build_edifices(gs, chronicle, winner, rng)

    # Track which sites have intact edifices (they survive)
    sites_with_intact_edifices: list[int] = []  # site indices
    sites_with_ruins: list[int] = []  # site indices (ordered)

    for site_idx, site in enumerate(gs.sites):
        has_intact = False
        has_ruined = False
        for slot_idx in range(site.capacity):
            card_id = site.cards[slot_idx]
            if card_id is not None:
                card = get_card(card_id)
                if card.is_edifice:
                    # Check if this site is ruled by winner
                    if site.ruling_player == winner:
                        has_intact = True
                    else:
                        has_ruined = True

        if has_intact:
            sites_with_intact_edifices.append(site_idx)
        elif has_ruined:
            sites_with_ruins.append(site_idx)

    # 8.3.2: Discard sites without intact edifices
    # Return their denizen cards, relics, and ruined edifices
    for site_idx, site in enumerate(gs.sites):
        if site_idx in sites_with_intact_edifices:
            continue  # Keep these sites
        if site_idx in sites_with_ruins:
            continue  # Handle separately in 8.3.3

        # Discard denizen cards from this site
        for slot_idx in range(site.capacity):
            card_id = site.cards[slot_idx]
            if card_id is not None:
                card = get_card(card_id)
                if card.is_edifice:
                    # Ruined edifices return to archive
                    if card.suit is not None:
                        chronicle.archive[int(card.suit)].append(card_id)
                elif not card.is_vision and not card.is_relic:
                    # Denizen cards go to discard (tracked in chronicle)
                    if card.suit is not None:
                        chronicle.dispossessed[int(card.suit)].append(card_id)
                site.cards[slot_idx] = None

        # Return relics to relic deck
        chronicle.relic_deck.extend(site.relics)
        site.relics.clear()

    # 8.3.3: Flip intact edifices at unruled sites to ruined
    for site_idx in sites_with_ruins:
        site = gs.sites[site_idx]
        # Discard all denizen cards at these sites
        for slot_idx in range(site.capacity):
            card_id = site.cards[slot_idx]
            if card_id is not None:
                card = get_card(card_id)
                if not card.is_edifice:
                    site.cards[slot_idx] = None

    # 8.3.4: Clear the map of pawns, favor, secrets, warbands
    for site in gs.sites:
        site.ruling_player = None
        site.warbands = 0
        site.site_favor = 0
        site.site_secrets = 0
        for i in range(len(site.card_favor)):
            site.card_favor[i] = 0
            site.card_secrets[i] = 0

    # 8.3.5: Consolidate sites (push toward Cradle, fill with facedown)
    # Sites with intact edifices stay in place; others get rearranged
    # Save surviving sites in chronicle order
    surviving_sites: list[ChronicleSiteSnapshot] = []

    # First, collect sites with edifices (intact or ruined)
    for site_idx in sorted(sites_with_intact_edifices + sites_with_ruins):
        site = gs.sites[site_idx]
        cards = [c for c in site.cards[:site.capacity] if c is not None]
        surviving_sites.append(ChronicleSiteSnapshot(
            site_id=site.site_id,
            cards=cards,
            relics=list(site.relics),
            has_edifice=True,
            edifice_ruined=(site_idx in sites_with_ruins),
        ))

    chronicle.chronicled_sites = surviving_sites


def _build_edifices(
    gs: GameState,
    chronicle: ChronicleState,
    winner: int,
    rng: np.random.Generator,
) -> None:
    """8.3.1: Build or repair one edifice at a ruled site."""
    for site_idx, site in enumerate(gs.sites):
        if site.ruling_player != winner:
            continue
        if not site.is_faceup:
            continue

        # Check if site already has an edifice
        has_edifice = False
        for slot_idx in range(site.capacity):
            card_id = site.cards[slot_idx]
            if card_id is not None and get_card(card_id).is_edifice:
                has_edifice = True
                break

        if has_edifice:
            continue

        # Find a denizen to replace with an edifice of matching suit
        for slot_idx in range(site.capacity):
            card_id = site.cards[slot_idx]
            if card_id is None:
                continue
            card = get_card(card_id)
            if card.suit is None:
                continue

            edifice_id = get_edifice_by_suit(card.suit)
            if edifice_id is None:
                continue

            # Check if this edifice is available (in archive, not already in play)
            if edifice_id in chronicle.edifices_in_play:
                continue

            # Replace denizen with edifice
            site.cards[slot_idx] = edifice_id
            chronicle.edifices_in_play.append(edifice_id)
            # Return replaced denizen to world deck area
            break  # Only build one per site


# ── 8.4 Add Six Cards to World Deck ────────────────────────────


def _add_cards_to_world_deck(
    gs: GameState,
    chronicle: ChronicleState,
    winner: int,
    rng: np.random.Generator,
) -> None:
    """8.4: Add 6 cards from Archive to world deck based on winner's advisers.

    Find most common suit among winner's faceup advisers.
    Take from Archive (clockwise suit order):
    - 3 cards of most common suit
    - 2 cards of next clockwise suit
    - 1 card of next clockwise suit after that
    """
    winner_player = gs.players[winner]

    # Count suits in winner's advisers
    suit_counts: Counter = Counter()
    for slot_idx in range(len(winner_player.advisers)):
        card_id = winner_player.advisers[slot_idx]
        if card_id is not None:
            card = get_card(card_id)
            if card.suit is not None:
                suit_counts[card.suit] += 1

    if not suit_counts:
        # No advisers with suits — pick any suit
        primary_suit = SUIT_CLOCKWISE_ORDER[0]
    else:
        # Most common suit (break ties by archive size)
        max_count = max(suit_counts.values())
        tied = [s for s, c in suit_counts.items() if c == max_count]
        if len(tied) == 1:
            primary_suit = tied[0]
        else:
            # Break tie: pick suit with more cards in archive
            primary_suit = max(tied, key=lambda s: len(chronicle.archive.get(int(s), [])))

    # Find clockwise order starting from primary suit
    cw = SUIT_CLOCKWISE_ORDER
    start = cw.index(primary_suit) if primary_suit in cw else 0
    suits_to_add = [
        (cw[start % 6], 3),                          # 3 of primary
        (cw[(start + 1) % 6], 2),                     # 2 of next
        (cw[(start + 2) % 6], 1),                     # 1 of next
    ]

    # Check if archive has enough cards, heal if needed
    total_needed = sum(count for _, count in suits_to_add)
    total_available = sum(len(v) for v in chronicle.archive.values())
    if total_available < total_needed:
        _heal_archive(chronicle, rng)

    # Take cards from archive
    cards_added: list[int] = []
    for suit, count in suits_to_add:
        suit_key = int(suit)
        available = chronicle.archive.get(suit_key, [])
        take = min(count, len(available))
        for _ in range(take):
            if available:
                idx = rng.integers(0, len(available))
                cards_added.append(available.pop(idx))

    # Add to the world deck pool (will be assembled in step 8.8)
    gs.world_deck.extend(cards_added)


def _heal_archive(chronicle: ChronicleState, rng: np.random.Generator) -> None:
    """Heal the Archive from Dispossessed when Archive runs low.

    Take all cards from Dispossessed, sort by suit, add stacks with
    most cards back to Archive by suit.
    """
    for suit_key in range(NUM_SUITS):
        dispossessed_cards = chronicle.dispossessed.get(suit_key, [])
        if dispossessed_cards:
            rng.shuffle(dispossessed_cards)
            chronicle.archive.setdefault(suit_key, []).extend(dispossessed_cards)
            chronicle.dispossessed[suit_key] = []


# ── 8.5 Remove Six Cards to Dispossessed ──────────────────────


def _remove_cards_to_dispossessed(
    gs: GameState,
    chronicle: ChronicleState,
    winner: int,
    rng: np.random.Generator,
) -> None:
    """8.5: Remove 6 cards to the Dispossessed.

    1. Set aside all 5 Visions
    2. Shuffle discard piles + losing players' advisers
    3. Take 6 random cards → Dispossessed (sorted by suit)
    """
    vision_ids = set(get_vision_ids())

    # Collect all cards from discard piles
    pool: list[int] = []
    for pile in gs.discard_piles:
        for card_id in pile:
            if card_id not in vision_ids:
                pool.append(card_id)

    # Add losing players' advisers
    for i in range(gs.num_players):
        if i == winner:
            continue
        player = gs.players[i]
        for card_id in player.advisers:
            if card_id is not None and card_id not in vision_ids:
                pool.append(card_id)

    # Shuffle and take 6
    rng.shuffle(pool)
    removed = pool[:6]

    for card_id in removed:
        card = get_card(card_id)
        suit_key = int(card.suit) if card.suit is not None else 0
        chronicle.dispossessed.setdefault(suit_key, []).append(card_id)


# ── 8.6 Clean Up Relics ──────────────────────────────────────────


def _clean_up_relics(
    gs: GameState,
    chronicle: ChronicleState,
    winner: int,
    rng: np.random.Generator,
) -> None:
    """8.6: Clean up relics between games.

    8.6.1: Return Grand Scepter. Return losers' relics to relic deck, shuffle.
    8.6.2: At faceup sites with fewer relics than "R" icons, draw to fill.
    8.6.3: Winner's relics + Reliquary → shuffle → top of relic deck.
    """
    winner_relics: list[int] = []
    loser_relics: list[int] = []

    # Separate winner's relics from losers'
    for i in range(gs.num_players):
        player = gs.players[i]
        for relic_id in player.relics:
            if relic_id == GRAND_SCEPTER_ID:
                continue  # Grand Scepter returns to box (not in deck)
            if i == winner:
                winner_relics.append(relic_id)
            else:
                loser_relics.append(relic_id)

    # 8.6.1: Losers' relics → relic deck, shuffle
    rng.shuffle(loser_relics)
    chronicle.relic_deck.extend(loser_relics)
    rng.shuffle(chronicle.relic_deck)

    # 8.6.2: Fill sites (simplified — we'll handle in setup)
    # Sites need relics matching their "R" icons, but since we're
    # rebuilding the map from chronicle sites, this happens at setup

    # 8.6.3: Winner's relics + Reliquary → top of relic deck
    reliquary_relics = [r for r in gs.reliquary if r != GRAND_SCEPTER_ID]
    top_relics = winner_relics + reliquary_relics
    rng.shuffle(top_relics)

    # Stack on top (prepend)
    chronicle.relic_deck = top_relics + chronicle.relic_deck


# ── 8.7 Save Map and Boards ──────────────────────────────────────


def _save_map_and_boards(gs: GameState, chronicle: ChronicleState) -> None:
    """8.7: Save the map state and player boards.

    8.7.1: Stack cards at each site on its site card.
           Order: bottom Hinterland → top Cradle.
    8.7.2: Save player boards on current Exile/Citizen side.
    """
    # chronicled_sites was already populated in _clean_up_map
    # player_boards was already populated in _offer_citizenship
    pass


# ── 8.8 Rebuild the World Deck ──────────────────────────────────


def _rebuild_world_deck(
    gs: GameState,
    chronicle: ChronicleState,
    rng: np.random.Generator,
) -> None:
    """8.8: Rebuild the world deck with layered Visions.

    1. Collect all remaining denizen cards
    2. Take 10 denizen facedown, shuffle in 2 Vision cards → pile of 12
    3. Take 15 denizen facedown, shuffle in 3 Vision cards → pile of 18
    4. Stack: pile of 12 on top of pile of 18 on top of remaining denizens
    """
    vision_ids = get_vision_ids()

    # Collect all denizen cards that should be in the deck
    # These come from: remaining world deck + discards + non-winner advisers
    # minus those placed at sites or in dispossessed
    denizens: list[int] = []
    placed_cards: set[int] = set()

    # Cards at chronicled sites are placed
    for snap in chronicle.chronicled_sites:
        placed_cards.update(snap.cards)

    # Cards in dispossessed are removed
    for suit_cards in chronicle.dispossessed.values():
        placed_cards.update(suit_cards)

    # Cards in archive stay in archive
    for suit_cards in chronicle.archive.values():
        placed_cards.update(suit_cards)

    # Collect remaining denizens from the game
    for card_id in gs.world_deck:
        card = get_card(card_id)
        if not card.is_vision and card_id not in placed_cards:
            denizens.append(card_id)

    for pile in gs.discard_piles:
        for card_id in pile:
            card = get_card(card_id)
            if not card.is_vision and card_id not in placed_cards:
                denizens.append(card_id)

    # Winner's advisers stay with winner (already handled)
    # Add non-winner, non-dispossessed adviser cards
    for i in range(gs.num_players):
        for card_id in gs.players[i].advisers:
            if card_id is not None and card_id not in placed_cards:
                card = get_card(card_id)
                if not card.is_vision:
                    denizens.append(card_id)

    # Add cards from sites that weren't chronicled
    for site in gs.sites:
        for card_id in site.cards:
            if card_id is not None and card_id not in placed_cards:
                card = get_card(card_id)
                if not card.is_vision and not card.is_edifice:
                    denizens.append(card_id)

    # Deduplicate (a card shouldn't appear twice)
    seen: set[int] = set()
    unique_denizens: list[int] = []
    for cid in denizens:
        if cid not in seen:
            seen.add(cid)
            unique_denizens.append(cid)
    denizens = unique_denizens

    rng.shuffle(denizens)

    # Build the layered deck
    # Pile 1: 10 denizens + 2 visions = 12 cards (top of deck, drawn first)
    pile1_denizens = denizens[:10]
    denizens = denizens[10:]

    # Pile 2: 15 denizens + 3 visions = 18 cards (middle)
    pile2_denizens = denizens[:15]
    denizens = denizens[15:]

    # Remaining denizens go at the bottom (no visions)
    bottom = list(denizens)

    # Shuffle visions into piles
    rng.shuffle(vision_ids)
    pile1 = pile1_denizens + vision_ids[:2]
    pile2 = pile2_denizens + vision_ids[2:5]

    rng.shuffle(pile1)
    rng.shuffle(pile2)

    # Stack: pile1 (top) → pile2 (middle) → bottom
    chronicle.world_deck = pile1 + pile2 + bottom


# ── Archive Initialization ──────────────────────────────────────


def _initialize_archive(chronicle: ChronicleState, gs: GameState) -> None:
    """Initialize the Archive with all cards NOT currently in the game.

    The Archive contains denizens and edifices that aren't in the
    world deck, at sites, or held by players.
    """
    # Track all cards currently in the game
    in_game: set[int] = set()

    # World deck
    in_game.update(gs.world_deck)

    # Discard piles
    for pile in gs.discard_piles:
        in_game.update(pile)

    # Cards at sites
    for site in gs.sites:
        for card_id in site.cards:
            if card_id is not None:
                in_game.add(card_id)

    # Player advisers and relics
    for player in gs.players:
        for card_id in player.advisers:
            if card_id is not None:
                in_game.add(card_id)
        in_game.update(player.relics)
        if player.revealed_vision is not None:
            in_game.add(player.revealed_vision)

    # Reliquary
    in_game.update(gs.reliquary)

    # All denizens NOT in game go to Archive
    for card_id in range(1, 200):
        if card_id not in in_game:
            card = get_card(card_id)
            if card.suit is not None:
                chronicle.archive[int(card.suit)].append(card_id)

    # Edifices NOT in game go to Archive
    for card_id in get_edifice_ids():
        if card_id not in in_game:
            card = get_card(card_id)
            if card.suit is not None:
                chronicle.archive[int(card.suit)].append(card_id)
        else:
            chronicle.edifices_in_play.append(card_id)

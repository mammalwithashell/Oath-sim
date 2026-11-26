use smallvec::SmallVec;

use crate::cards::get_card;
use crate::engine::setup::build_world_deck_with_visions;
use crate::state::*;
use crate::types::*;

/// Apply the full §8 Chronicle transition after a game finishes, producing a ChronicleState
/// for the next game in the lineage.
pub fn apply_chronicle(gs: &mut GameState) -> ChronicleState {
    let winner = gs.winner.unwrap_or(0);
    let next_oath = gs.vowed_oath.unwrap_or(gs.oath_goal);

    // 1. Player boards (§8.2): if Exile won, previous Citizens flip to Exile
    let mut player_boards = Vec::with_capacity(gs.num_players as usize - 1);
    let winner_was_exile = gs.players[winner as usize].role == Role::Exile;
    for p in 1..gs.num_players as usize {
        if winner_was_exile {
            player_boards.push(Role::Exile);
        } else {
            player_boards.push(gs.players[p].role);
        }
    }

    // 2. Clean up map & edifices (§8.3)
    // Forest Temple (OATH-203): do not discard sites with any Beast cards
    let has_forest_temple = gs
        .sites
        .iter()
        .any(|s| s.is_faceup && s.cards.contains(&EDIFICE_FOREST_TEMPLE));

    let mut chronicled_sites: Vec<ChronicleSiteSnapshot> = Vec::new();
    let mut site_deck = gs.site_deck.clone();
    let mut discard_pool: Vec<CardId> = Vec::new();
    for pile in &gs.discard_piles {
        discard_pool.extend(pile.iter().copied());
    }
    for p in 0..gs.num_players as usize {
        if p != winner as usize {
            for &adv in &gs.players[p].advisers {
                if adv != CARD_EMPTY {
                    discard_pool.push(adv);
                }
            }
        }
    }

    for si in 0..MAX_SITES {
        let s = &gs.sites[si];
        let has_intact_edifice = s.cards[..s.capacity as usize]
            .iter()
            .any(|&c| c != CARD_EMPTY && get_card(c).card_type == CardType::Edifice && !get_card(c).edifice_is_ruined);
        let has_beast = s.cards[..s.capacity as usize]
            .iter()
            .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(Suit::Beast));

        let keep_site = s.is_faceup
            && (gs.player_rules_site(winner, si as SiteIndex)
                || has_intact_edifice
                || (has_forest_temple && has_beast));

        if keep_site {
            let mut snap_cards: SmallVec<[CardId; 3]> = SmallVec::new();
            for &cid in &s.cards[..s.capacity as usize] {
                if cid == CARD_EMPTY {
                    continue;
                }
                let def = get_card(cid);
                if def.card_type == CardType::Edifice && !def.edifice_is_ruined {
                    // Ruin intact edifices at sites not ruled by winner
                    if !gs.player_rules_site(winner, si as SiteIndex) {
                        if let Some(ruined_id) = def.edifice_flip_id {
                            snap_cards.push(ruined_id);
                        }
                    } else {
                        snap_cards.push(cid);
                    }
                } else {
                    snap_cards.push(cid);
                }
            }
            chronicled_sites.push(ChronicleSiteSnapshot {
                site_id: s.site_id,
                cards: snap_cards,
                relics: s.relics.iter().copied().take(3).collect(),
            });
        } else {
            site_deck.push(s.site_id);
            for &cid in &s.cards[..s.capacity as usize] {
                if cid != CARD_EMPTY && get_card(cid).card_type == CardType::Denizen {
                    discard_pool.push(cid);
                }
            }
        }
    }

    // 3. Add 6 cards from Archive based on winner's most common adviser suit (§8.4)
    let mut suit_counts = [0u8; NUM_SUITS];
    for &adv in &gs.players[winner as usize].advisers {
        if adv != CARD_EMPTY {
            if let Some(suit) = get_card(adv).suit {
                suit_counts[suit as usize] += 1;
            }
        }
    }
    let primary_suit = Suit::CLOCKWISE
        .iter()
        .copied()
        .max_by_key(|&s| suit_counts[s as usize])
        .unwrap_or(Suit::Order);
    let cw_pos = Suit::CLOCKWISE
        .iter()
        .position(|&s| s == primary_suit)
        .unwrap_or(0);

    let mut archive = gs.archive.clone();
    let mut added_denizens: Vec<CardId> = Vec::new();
    let add_counts = [(0usize, 3usize), (1, 2), (2, 1)];
    for (offset, count) in add_counts {
        let suit = Suit::CLOCKWISE[(cw_pos + offset) % NUM_SUITS];
        for _ in 0..count {
            if let Some(cid) = archive[suit as usize].pop() {
                added_denizens.push(cid);
            }
        }
    }

    // 4. Remove 6 random cards to Dispossessed (§8.5)
    let mut dispossessed = gs.dispossessed.clone();
    let mut denizen_discards: Vec<CardId> = discard_pool
        .into_iter()
        .filter(|&c| get_card(c).card_type == CardType::Denizen)
        .collect();
    gs.rng.shuffle(&mut denizen_discards);
    for _ in 0..6 {
        if let Some(cid) = denizen_discards.pop() {
            dispossessed.push(cid);
        }
    }

    // 5. Rebuild World Deck (§8.8)
    let mut next_denizens: Vec<CardId> = gs
        .world_deck
        .iter()
        .copied()
        .filter(|&c| get_card(c).card_type == CardType::Denizen)
        .collect();
    next_denizens.extend(denizen_discards);
    next_denizens.extend(added_denizens);
    let world_deck = build_world_deck_with_visions(next_denizens, &mut gs.rng);

    // 6. Clean up Relics (§8.6)
    let mut relic_deck: Vec<CardId> = gs.relic_deck.clone();
    for p in 0..gs.num_players as usize {
        if p != winner as usize {
            for &rid in &gs.players[p].relics {
                if rid != CARD_GRAND_SCEPTER {
                    relic_deck.push(rid);
                }
            }
        }
    }
    gs.rng.shuffle(&mut relic_deck);
    let mut top_relics: Vec<CardId> = gs
        .players[winner as usize]
        .relics
        .iter()
        .copied()
        .filter(|&r| r != CARD_GRAND_SCEPTER)
        .collect();
    top_relics.extend(gs.reliquary.iter().copied());
    gs.rng.shuffle(&mut top_relics);
    relic_deck.extend(top_relics);

    gs.rng.shuffle(&mut site_deck);

    ChronicleState {
        archive,
        dispossessed,
        chronicled_sites,
        site_deck,
        relic_deck,
        world_deck,
        oath_goal: next_oath,
        player_boards,
        last_winner: Some(winner),
        games_played: 1,
    }
}

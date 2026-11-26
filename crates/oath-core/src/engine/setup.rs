use smallvec::SmallVec;
use std::collections::VecDeque;

use crate::cards::get_card;
use crate::engine::turn::start_turn;
use crate::rng::FastRng;
use crate::state::*;
use crate::types::*;

/// First-game canonical sites (8 sites across Cradle, Provinces, Hinterland).
const FIRST_GAME_SITES: [CardId; 8] = [
    SITE_PLAINS,         // 0: Cradle
    SITE_MOUNTAIN,       // 1: Cradle
    SITE_ROCKY_COAST,    // 2: Provinces
    SITE_LUSH_COAST,     // 3: Provinces
    SITE_NARROW_PASS,    // 4: Provinces
    SITE_MINE,           // 5: Hinterland
    SITE_WASTES,         // 6: Hinterland
    SITE_SALT_FLATS,     // 7: Hinterland
];

#[derive(Debug, Clone)]
pub struct GameConfig {
    pub num_players: u8,
    pub seed: u64,
    pub first_game: bool,
    pub oath_goal: Option<OathGoal>,
    pub chronicle_enabled: bool,
}

impl Default for GameConfig {
    fn default() -> Self {
        Self {
            num_players: 4,
            seed: 42,
            first_game: true,
            oath_goal: None,
            chronicle_enabled: false,
        }
    }
}

pub fn create_initial_state(config: &GameConfig, chronicle: Option<&ChronicleState>) -> GameState {
    let num_players = config.num_players.clamp(2, MAX_PLAYERS as u8);
    let mut rng = FastRng::seed_from_u64(config.seed);

    let oath_goal = chronicle
        .map(|c| c.oath_goal)
        .or(config.oath_goal)
        .unwrap_or(OathGoal::Supremacy);
    let successor_goal = oath_goal.successor_goal();

    // Build Players
    let mut players: [PlayerState; MAX_PLAYERS] = std::array::from_fn(|i| {
        let role = if i == 0 {
            Role::Chancellor
        } else if let Some(ch) = chronicle {
            ch.player_boards
                .get(i - 1)
                .copied()
                .unwrap_or(Role::Exile)
        } else {
            Role::Exile
        };
        PlayerState::new(role, i as PlayerId)
    });

    // Build Relics (211..=230 are standard relics; 231 is Grand Scepter)
    let mut relic_deck: Vec<CardId> = if let Some(ch) = chronicle {
        ch.relic_deck.clone()
    } else {
        let mut r: Vec<CardId> = (211..=230).collect();
        rng.shuffle(&mut r);
        r
    };

    // Grand Scepter goes to Chancellor (§3.6)
    players[0].relics.push(CARD_GRAND_SCEPTER);

    // Reliquary: 4 relics drawn from relic deck
    let mut reliquary: SmallVec<[CardId; 4]> = SmallVec::new();
    for _ in 0..MAX_RELIQUARY {
        if let Some(r) = relic_deck.pop() {
            reliquary.push(r);
        }
    }

    // Sites & site_deck
    let mut site_deck: Vec<CardId>;
    let mut sites: [SiteState; MAX_SITES] = std::array::from_fn(|i| {
        SiteState::empty(FIRST_GAME_SITES[i], Region::from_site_index(i as u8))
    });

    if let Some(ch) = chronicle {
        site_deck = ch.site_deck.clone();
        for i in 0..MAX_SITES {
            if let Some(snap) = ch.chronicled_sites.get(i) {
                sites[i] = SiteState::empty(snap.site_id, Region::from_site_index(i as u8));
                sites[i].is_faceup = i < 4; // Cradle + top Provinces start faceup
                for (slot, &cid) in snap.cards.iter().enumerate() {
                    if slot < MAX_CARDS_PER_SITE {
                        sites[i].cards[slot] = cid;
                    }
                }
                for &rid in &snap.relics {
                    sites[i].relics.push(rid);
                }
            } else if let Some(sid) = site_deck.pop() {
                sites[i] = SiteState::empty(sid, Region::from_site_index(i as u8));
            }
        }
    } else if config.first_game {
        let first_set: std::collections::HashSet<CardId> = FIRST_GAME_SITES.into_iter().collect();
        site_deck = (237..=259).filter(|id| !first_set.contains(id)).collect();
        rng.shuffle(&mut site_deck);
        for i in 0..MAX_SITES {
            sites[i] = SiteState::empty(FIRST_GAME_SITES[i], Region::from_site_index(i as u8));
        }
    } else {
        let mut all_sites: Vec<CardId> = (237..=259).collect();
        rng.shuffle(&mut all_sites);
        for i in 0..MAX_SITES {
            let sid = all_sites.pop().unwrap();
            sites[i] = SiteState::empty(sid, Region::from_site_index(i as u8));
        }
        site_deck = all_sites;
    }

    // Build World Deck, Archive, Dispossessed
    let mut archive: [Vec<CardId>; NUM_SUITS] = std::array::from_fn(|_| Vec::new());
    let dispossessed: Vec<CardId>;
    let mut world_deck: Vec<CardId>;

    if let Some(ch) = chronicle {
        archive = ch.archive.clone();
        dispossessed = ch.dispossessed.clone();
        world_deck = ch.world_deck.clone();
    } else {
        dispossessed = Vec::new();
        let mut all_denizens: Vec<CardId> = (1..=198).collect();
        rng.shuffle(&mut all_denizens);
        // Take 54 denizens for the world deck, rest into Archive by suit
        let deck_denizens: Vec<CardId> = all_denizens.drain(..54.min(all_denizens.len())).collect();
        for cid in all_denizens {
            if let Some(suit) = get_card(cid).suit {
                archive[suit as usize].push(cid);
            }
        }
        world_deck = build_world_deck_with_visions(deck_denizens, &mut rng);
    }

    // Reveal initial faceup sites (Cradle 0,1 and Provinces 2,3 faceup; 4..7 facedown)
    let favor_per_bank = if num_players >= 5 { 4 } else { 3 };
    let favor_banks = [favor_per_bank; NUM_SUITS];
    let mut shared_secrets = MAX_SECRETS_TOTAL;

    // Subtract starting player secrets (1 each) + Darkest Secret (1)
    shared_secrets = shared_secrets.saturating_sub(num_players + 1);

    // Reveal first 4 sites (Cradle + 2 Provinces)
    for i in 0..4 {
        sites[i].is_faceup = true;
        if chronicle.is_none() {
            let def = get_card(sites[i].site_id);
            sites[i].site_favor = def.starting_favor;
            let take_sec = def.starting_secrets.min(shared_secrets);
            sites[i].site_secrets = take_sec;
            shared_secrets -= take_sec;
            for _ in 0..def.starting_relics {
                if let Some(r) = relic_deck.pop() {
                    sites[i].relics.push(r);
                }
            }
            // Populate 1 starting denizen on Cradle sites for immediate playability
            if i < 2 && sites[i].capacity > 0 {
                if let Some(cid) = draw_non_vision(&mut world_deck) {
                    sites[i].cards[0] = cid;
                }
            }
        }
    }

    // Chancellor starting warbands (§3.8): 3 on board, 2 on top Cradle site, 1 on other faceup sites with cards
    players[0].warbands_board = 3;
    players[0].warbands_bank = MAX_WARBANDS_CHANCELLOR - 3;
    sites[0].ruling_player = Some(0);
    sites[0].warbands = 2;
    sites[0].warband_color = Some(0);
    players[0].warbands_bank -= 2;

    for i in 1..4 {
        if sites[i].num_cards() > 0 && players[0].warbands_bank > 0 {
            sites[i].ruling_player = Some(0);
            sites[i].warbands = 1;
            sites[i].warband_color = Some(0);
            players[0].warbands_bank -= 1;
        }
    }

    // Other players: 3 warbands on board, pawn on Cradle site 0
    for p in 1..num_players as usize {
        players[p].warbands_board = 3;
        players[p].warbands_bank = players[p].warbands_bank.saturating_sub(3);
        players[p].pawn_site = (p as u8) % 2; // spread across Cradle sites
    }

    // Banners (§3.4, §3.11)
    let peoples_favor_holder = if oath_goal == OathGoal::People {
        Some(0)
    } else {
        None
    };
    let darkest_secret_holder = if oath_goal == OathGoal::Devotion {
        Some(0)
    } else {
        None
    };

    // Discard piles: 1 card from bottom of world deck into each region's discard pile (§3.12)
    let mut discard_piles: [Vec<CardId>; NUM_REGIONS] = std::array::from_fn(|_| Vec::new());
    for r in 0..NUM_REGIONS {
        if let Some(cid) = draw_non_vision_from_bottom(&mut world_deck) {
            discard_piles[r].push(cid);
        }
    }

    // Each player draws 1 starting facedown adviser from bottom of world deck (§3.13-15)
    let mut visions_drawn = 0u8;
    for p in 0..num_players as usize {
        if let Some(cid) = draw_from_bottom(&mut world_deck) {
            if get_card(cid).card_type == CardType::Vision {
                visions_drawn = (visions_drawn + 1).min(MAX_VISIONS_DRAWN);
            }
            players[p].advisers[0] = cid;
            players[p].adviser_faceup[0] = false;
        }
    }

    let mut turn_order = [0u8; MAX_PLAYERS];
    for i in 0..MAX_PLAYERS {
        turn_order[i] = i as PlayerId;
    }

    let mut gs = GameState {
        players,
        num_players,
        current_player: 0,
        turn_order,
        sites,
        world_deck,
        discard_piles,
        relic_deck,
        dispossessed,
        archive,
        site_deck,
        reliquary,
        favor_banks,
        shared_secrets,
        peoples_favor_holder,
        peoples_favor_tokens: 1,
        peoples_favor_is_mob: false,
        darkest_secret_holder,
        darkest_secret_tokens: 1,
        oathkeeper_holder: Some(0),
        oathkeeper_side: TitleSide::Oathkeeper,
        oath_goal,
        successor_goal,
        round_number: 1,
        visions_drawn,
        turn_in_round: 0,
        phase: Phase::Wake,
        decision: DecisionPoint::TurnAct { player: 0 },
        effect_stack: Vec::new(),
        search: None,
        campaign: None,
        deal: None,
        active_contracts: SmallVec::new(),
        talk_log: VecDeque::new(),
        knowledge: std::array::from_fn(|_| KnowledgeState::default()),
        obsidian_cage_warbands: [0; MAX_PLAYERS],
        scepter_taken_this_turn: false,
        used_card_powers_this_turn: SmallVec::new(),
        supply_spent_this_turn: 0,
        actions_taken_this_turn: 0,
        is_game_over: false,
        winner: None,
        win_type: None,
        vowed_oath: None,
        chronicle_enabled: config.chronicle_enabled,
        rng,
        step_count: 0,
    };

    // Start first player's Wake phase
    start_turn(&mut gs);
    gs
}

/// Build World Deck per §8.8:
/// - Bottom: remaining denizens
/// - Middle: 15 denizens + 3 visions shuffled
/// - Top (end of Vec, popped first): 10 denizens + 2 visions shuffled
pub fn build_world_deck_with_visions(mut denizens: Vec<CardId>, rng: &mut FastRng) -> Vec<CardId> {
    rng.shuffle(&mut denizens);
    let mut visions: Vec<CardId> = vec![
        CARD_CONSPIRACY,
        CARD_VISION_FAITH,
        CARD_VISION_REBELLION,
        CARD_VISION_SANCTUARY,
        CARD_VISION_CONQUEST,
    ];
    rng.shuffle(&mut visions);

    let top_n = 10.min(denizens.len());
    let mut top_pile: Vec<CardId> = denizens.drain(..top_n).collect();
    top_pile.extend(visions.drain(..2.min(visions.len())));
    rng.shuffle(&mut top_pile);

    let mid_n = 15.min(denizens.len());
    let mut mid_pile: Vec<CardId> = denizens.drain(..mid_n).collect();
    mid_pile.extend(visions.drain(..));
    rng.shuffle(&mut mid_pile);

    let mut deck = denizens; // bottom
    deck.extend(mid_pile);
    deck.extend(top_pile); // top (Vec::pop draws from here)
    deck
}

fn draw_non_vision(deck: &mut Vec<CardId>) -> Option<CardId> {
    for i in (0..deck.len()).rev() {
        if get_card(deck[i]).card_type != CardType::Vision {
            return Some(deck.remove(i));
        }
    }
    None
}

fn draw_non_vision_from_bottom(deck: &mut Vec<CardId>) -> Option<CardId> {
    for i in 0..deck.len() {
        if get_card(deck[i]).card_type != CardType::Vision {
            return Some(deck.remove(i));
        }
    }
    None
}

fn draw_from_bottom(deck: &mut Vec<CardId>) -> Option<CardId> {
    if deck.is_empty() {
        None
    } else {
        Some(deck.remove(0))
    }
}

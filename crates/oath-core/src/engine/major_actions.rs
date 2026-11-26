use smallvec::SmallVec;

use crate::cards::{self, get_card};
use crate::engine::deals::check_contract_violation_banner;
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

// ── TRAVEL (§5.6) ─────────────────────────────────────────────────────────

pub fn travel_cost(gs: &GameState, player: PlayerId, target_site: SiteIndex) -> u8 {
    let p = &gs.players[player as usize];
    let from_idx = p.pawn_site;
    let from_site = &gs.sites[from_idx as usize];
    let to_site = &gs.sites[target_site as usize];

    // Shrouded Wood (OATH-255): Travel cost from here is always 2 Supply
    if from_site.site_id == SITE_SHROUDED_WOOD && from_site.is_faceup {
        return 2;
    }

    // Coast-to-Coast (Barren/Lush/Rocky Coast): Travel cost is 1 Supply
    if from_site.is_faceup
        && to_site.is_faceup
        && get_card(from_site.site_id).is_coast
        && get_card(to_site.site_id).is_coast
    {
        return 1;
    }

    let base: i8 = match (from_site.region, to_site.region) {
        (Region::Cradle, Region::Cradle) => 1,
        (Region::Provinces, Region::Provinces) => 2,
        (Region::Hinterland, Region::Hinterland) => 3,
        (Region::Cradle, Region::Provinces) | (Region::Provinces, Region::Cradle) => 2,
        (Region::Provinces, Region::Hinterland) | (Region::Hinterland, Region::Provinces) => 2,
        (Region::Cradle, Region::Hinterland) | (Region::Hinterland, Region::Cradle) => 4,
    };

    // Charming Valley (OATH-240): +1 Supply when traveling from here
    let mut cost = base;
    if from_site.site_id == SITE_CHARMING_VALLEY && from_site.is_faceup {
        cost += 1;
    }

    // Denizen Travel modifiers (e.g., Forest Paths, Rain Boots, etc.)
    cost += cards::denizens::travel_cost_modifier(gs, player, from_idx, target_site);

    cost.max(0) as u8
}

pub fn can_travel(gs: &GameState, player: PlayerId, target_site: SiteIndex) -> bool {
    if target_site as usize >= MAX_SITES {
        return false;
    }
    let p = &gs.players[player as usize];
    if p.pawn_site == target_site {
        return false;
    }
    let from_site = &gs.sites[p.pawn_site as usize];
    let to_site = &gs.sites[target_site as usize];

    let ignores_narrow_and_hidden =
        from_site.is_faceup && from_site.site_id == SITE_SHROUDED_WOOD;
    let ignores_narrow = ignores_narrow_and_hidden
        || (from_site.is_faceup
            && to_site.is_faceup
            && get_card(from_site.site_id).is_coast
            && get_card(to_site.site_id).is_coast);

    // Narrow Pass (OATH-250): when traveling from another region to Narrow Pass's region,
    // must travel to Narrow Pass (unless ignored)
    if !ignores_narrow && from_site.region != to_site.region {
        for si in 0..MAX_SITES as u8 {
            if gs.sites[si as usize].is_faceup
                && gs.sites[si as usize].region == to_site.region
                && gs.sites[si as usize].site_id == SITE_NARROW_PASS
                && si != target_site
            {
                return false;
            }
        }
    }

    // The Hidden Place (OATH-258): must flip 1 faceup secret to travel here (unless ignored)
    if !ignores_narrow_and_hidden
        && to_site.is_faceup
        && to_site.site_id == SITE_THE_HIDDEN_PLACE
        && p.secrets_faceup == 0
    {
        return false;
    }

    // Vow of Union (OATH-185): cannot travel from a site you rule if any warbands are on your board
    if gs.player_has_card_access(player, 185)
        && gs.player_rules_site(player, p.pawn_site)
        && p.warbands_board > 0
    {
        return false;
    }

    // Toll Roads (OATH-118): enemies must pay 1 favor to travel to sites ruled by Toll Roads' ruler
    if is_blocked_by_enemy_card(gs, player, 118) && to_site.ruling_player.is_some() && p.favor < 1 {
        return false;
    }

    // Buried Giant (OATH-239): can flip 1 secret to travel for 0 supply
    let cost = travel_cost(gs, player, target_site);
    if p.supply >= cost {
        return true;
    }
    if from_site.is_faceup && from_site.site_id == SITE_BURIED_GIANT && p.secrets_faceup > 0 {
        return true;
    }
    false
}

pub fn execute_travel(gs: &mut GameState, player: PlayerId, target_site: SiteIndex, free: bool) {
    let from_idx = gs.players[player as usize].pawn_site;
    let from_site_id = gs.sites[from_idx as usize].site_id;
    let from_faceup = gs.sites[from_idx as usize].is_faceup;
    let to_site_id = gs.sites[target_site as usize].site_id;
    let to_faceup = gs.sites[target_site as usize].is_faceup;

    if !free {
        let cost = travel_cost(gs, player, target_site);
        if gs.players[player as usize].supply >= cost {
            gs.players[player as usize].supply -= cost;
            gs.supply_spent_this_turn += cost;
        } else if from_faceup
            && from_site_id == SITE_BURIED_GIANT
            && gs.players[player as usize].secrets_faceup > 0
        {
            gs.players[player as usize].secrets_faceup -= 1;
            gs.players[player as usize].secrets_facedown += 1;
        }

        // Hidden Place secret flip (unless ignored by Shrouded Wood)
        if !(from_faceup && from_site_id == SITE_SHROUDED_WOOD)
            && to_faceup
            && to_site_id == SITE_THE_HIDDEN_PLACE
            && gs.players[player as usize].secrets_faceup > 0
        {
            gs.players[player as usize].secrets_faceup -= 1;
            gs.players[player as usize].secrets_facedown += 1;
        }
    }

    gs.players[player as usize].pawn_site = target_site;
    if !gs.sites[target_site as usize].is_faceup {
        reveal_site(gs, target_site);
    }

    // Dragonskin Drum (OATH-230): after traveling, gain 1 warband
    if gs.players[player as usize].has_relic(RELIC_DRAGONSKIN_DRUM) {
        gain_warbands(gs, player, 1);
    }

    // Denizen after-travel hooks
    cards::denizens::on_after_travel(gs, player, from_idx, target_site);
    gs.actions_taken_this_turn += 1;
}

pub fn reveal_site(gs: &mut GameState, site_idx: SiteIndex) {
    let site = &mut gs.sites[site_idx as usize];
    if site.is_faceup {
        return;
    }
    site.is_faceup = true;
    let def = get_card(site.site_id);
    site.capacity = def.capacity;
    site.site_favor = def.starting_favor;
    let take_sec = def.starting_secrets.min(gs.shared_secrets);
    site.site_secrets = take_sec;
    gs.shared_secrets -= take_sec;
    for _ in 0..def.starting_relics {
        if let Some(rid) = gs.relic_deck.pop() {
            site.relics.push(rid);
        }
    }
}

// ── MUSTER (§5.2) ─────────────────────────────────────────────────────────

pub fn muster_supply_cost(gs: &GameState, player: PlayerId, cid: CardId) -> u8 {
    // Animal Playmates (OATH-040): 0 Supply when mustering on Beast card
    if gs.player_has_card_access(player, 40) && get_card(cid).suit == Some(Suit::Beast) {
        return 0;
    }
    1
}

pub fn can_muster(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];
    if !site.is_faceup || slot >= site.capacity {
        return false;
    }
    let cid = site.cards[slot as usize];
    if cid == CARD_EMPTY {
        return false;
    }
    let sup_cost = muster_supply_cost(gs, player, cid);
    if p.supply < sup_cost {
        return false;
    }
    // Initiation Rite (OATH-073): must place 1 secret instead of 1 favor
    let uses_secret = gs.player_has_card_access(player, 73);
    if uses_secret {
        if p.secrets_faceup < 1 {
            return false;
        }
    } else if p.favor < 1 {
        return false;
    }
    let def = get_card(cid);
    if def.card_type != CardType::Denizen && !(def.card_type == CardType::Edifice && !def.edifice_is_ruined) {
        return false;
    }
    // Pressgangs (OATH-006): can muster on cards with favor/secrets on them
    let has_pressgangs = gs.player_has_card_access(player, 6);
    if !has_pressgangs && (site.card_favor[slot as usize] > 0 || site.card_secrets[slot as usize] > 0) {
        return false;
    }
    // Forest Council (OATH-194): enemies cannot muster from Beast cards
    if def.suit == Some(Suit::Beast) && is_blocked_by_enemy_card(gs, player, 194) {
        return false;
    }
    // Need at least 1 warband in personal/imperial bank
    warband_bank_for(gs, player) > 0
}

pub fn execute_muster(gs: &mut GameState, player: PlayerId, slot: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let cid = gs.sites[site_idx as usize].cards[slot as usize];
    let sup_cost = muster_supply_cost(gs, player, cid);
    gs.players[player as usize].supply -= sup_cost;
    gs.supply_spent_this_turn += sup_cost;
    if gs.player_has_card_access(player, 73) {
        gs.players[player as usize].secrets_faceup -= 1;
        gs.sites[site_idx as usize].card_secrets[slot as usize] += 1;
    } else {
        gs.players[player as usize].favor -= 1;
        gs.sites[site_idx as usize].card_favor[slot as usize] += 1;
    }

    let mut gain = 2u8;
    // River (OATH-252): +1 warband if you rule this site
    if gs.sites[site_idx as usize].site_id == SITE_RIVER && gs.player_rules_site(player, site_idx) {
        gain += 1;
    }
    // Ring of Devotion (OATH-222): +2 warbands when mustering
    if gs.players[player as usize].has_relic(RELIC_RING_OF_DEVOTION) {
        gain += 2;
    }
    gain += cards::denizens::muster_bonus(gs, player, site_idx, slot);
    gain_warbands(gs, player, gain);
    // Knights Errant (OATH-120): after mustering, +2 supply for campaign
    if gs.player_has_card_access(player, 120) {
        gs.players[player as usize].supply =
            (gs.players[player as usize].supply + 2).min(MAX_SUPPLY);
    }
    gs.actions_taken_this_turn += 1;
}

// ── TRADE (§5.3) ──────────────────────────────────────────────────────────

pub fn trade_supply_cost(gs: &GameState, player: PlayerId, card_id: CardId) -> u8 {
    // Cup of Plenty (OATH-217): 0 Supply if card matches any faceup adviser
    if gs.players[player as usize].has_relic(RELIC_CUP_OF_PLENTY) {
        if let Some(suit) = get_card(card_id).suit {
            if gs.players[player as usize].has_faceup_adviser_suit(suit) {
                return 0;
            }
        }
    }
    // Birdsong (OATH-176): 0 Supply when trading with Beast or Nomad card
    if gs.player_has_card_access(player, 176)
        && matches!(get_card(card_id).suit, Some(Suit::Beast) | Some(Suit::Nomad))
    {
        return 0;
    }
    1
}

pub fn can_trade_favor(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];
    if !site.is_faceup || slot >= site.capacity {
        return false;
    }
    let cid = site.cards[slot as usize];
    if cid == CARD_EMPTY {
        return false;
    }
    let def = get_card(cid);
    if def.card_type != CardType::Denizen && !(def.card_type == CardType::Edifice && !def.edifice_is_ruined) {
        return false;
    }
    if site.card_favor[slot as usize] > 0 || site.card_secrets[slot as usize] > 0 {
        return false;
    }
    let cost = trade_supply_cost(gs, player, cid);
    if p.supply < cost || p.secrets_faceup < 1 {
        return false;
    }
    // Vow of Poverty (OATH-193): cannot gain favor from Trade
    if gs.player_has_card_access(player, 193) {
        return false;
    }
    // Forest Council (OATH-194)
    if def.suit == Some(Suit::Beast) && is_blocked_by_enemy_card(gs, player, 194) {
        return false;
    }
    // Curfew (OATH-119): enemies must pay 1 favor to Curfew's ruler
    if is_blocked_by_enemy_card(gs, player, 119) && p.favor < 1 {
        return false;
    }
    let Some(suit) = def.suit else { return false };
    gs.favor_banks[suit as usize] > 0
}

pub fn execute_trade_favor(gs: &mut GameState, player: PlayerId, slot: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let cid = gs.sites[site_idx as usize].cards[slot as usize];
    let cost = trade_supply_cost(gs, player, cid);
    gs.players[player as usize].supply -= cost;
    gs.supply_spent_this_turn += cost;
    gs.players[player as usize].secrets_faceup -= 1;
    gs.sites[site_idx as usize].card_secrets[slot as usize] += 1;

    pay_curfew_if_needed(gs, player);

    if let Some(suit) = get_card(cid).suit {
        let matching = gs.players[player as usize].faceup_adviser_suit_count(suit);
        let mut amount = 1 + matching;
        amount += cards::denizens::trade_favor_bonus(gs, player, suit);
        let actual = amount.min(gs.favor_banks[suit as usize]);
        gs.favor_banks[suit as usize] -= actual;
        gs.players[player as usize].favor += actual;
    }
    gs.actions_taken_this_turn += 1;
}

pub fn can_trade_secrets(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];
    if !site.is_faceup || slot >= site.capacity {
        return false;
    }
    let cid = site.cards[slot as usize];
    if cid == CARD_EMPTY {
        return false;
    }
    let def = get_card(cid);
    if def.card_type != CardType::Denizen && !(def.card_type == CardType::Edifice && !def.edifice_is_ruined) {
        return false;
    }
    if site.card_favor[slot as usize] > 0 || site.card_secrets[slot as usize] > 0 {
        return false;
    }
    let cost = trade_supply_cost(gs, player, cid);
    let extra_curfew = if is_blocked_by_enemy_card(gs, player, 119) { 1 } else { 0 };
    if p.supply < cost || p.favor < 2 + extra_curfew {
        return false;
    }
    if def.suit == Some(Suit::Beast) && is_blocked_by_enemy_card(gs, player, 194) {
        return false;
    }
    let Some(suit) = def.suit else { return false };
    p.faceup_adviser_suit_count(suit) > 0 && gs.shared_secrets > 0
}

pub fn execute_trade_secrets(gs: &mut GameState, player: PlayerId, slot: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let cid = gs.sites[site_idx as usize].cards[slot as usize];
    let cost = trade_supply_cost(gs, player, cid);
    gs.players[player as usize].supply -= cost;
    gs.supply_spent_this_turn += cost;
    gs.players[player as usize].favor -= 2;
    gs.sites[site_idx as usize].card_favor[slot as usize] += 2;

    pay_curfew_if_needed(gs, player);

    if let Some(suit) = get_card(cid).suit {
        let matching = gs.players[player as usize].faceup_adviser_suit_count(suit);
        let amount = matching + cards::denizens::trade_secrets_bonus(gs, player, suit);
        let actual = amount.min(gs.shared_secrets);
        gs.shared_secrets -= actual;
        gs.players[player as usize].secrets_faceup += actual;
    }
    gs.actions_taken_this_turn += 1;
}

fn pay_curfew_if_needed(gs: &mut GameState, player: PlayerId) {
    if is_blocked_by_enemy_card(gs, player, 119) && gs.players[player as usize].favor > 0 {
        gs.players[player as usize].favor -= 1;
        if let Some(ruler) = crate::engine::turn::find_card_ruler(gs, 119) {
            if gs.is_imperial(ruler) {
                let c = gs.chancellor_index();
                gs.players[c as usize].favor += 1;
            } else {
                gs.players[ruler as usize].favor += 1;
            }
        } else {
            // Bandits: burn to smallest favor bank
            let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
            gs.favor_banks[min_i] += 1;
        }
    }
}

// ── SEARCH (§5.1) ─────────────────────────────────────────────────────────

pub fn search_deck_cost(gs: &GameState, player: PlayerId) -> u8 {
    let mut cost: i8 = match gs.visions_drawn {
        0..=1 => 2,
        2..=3 => 3,
        _ => 4,
    };
    cost += cards::denizens::search_cost_modifier(gs, player);
    cost.max(1) as u8
}

pub fn can_search_deck(gs: &GameState, player: PlayerId) -> bool {
    !gs.world_deck.is_empty() && gs.players[player as usize].supply >= search_deck_cost(gs, player)
}

pub fn can_search_discard(gs: &GameState, player: PlayerId) -> bool {
    let site = &gs.sites[gs.players[player as usize].pawn_site as usize];
    let any_region_access = gs.player_has_card_access(player, 11) // Errand Boy
        || gs.player_has_card_access(player, 64); // Observatory
    let has_cards = !gs.discard_piles[site.region as usize].is_empty()
        || (any_region_access && gs.discard_piles.iter().any(|p| !p.is_empty()));
    let forced_labor_ok = !is_blocked_by_enemy_card(gs, player, 112) || gs.players[player as usize].favor >= 1;
    has_cards && forced_labor_ok && gs.players[player as usize].supply >= 2
}

pub fn execute_search(gs: &mut GameState, player: PlayerId, from_deck: bool) {
    let site_idx = gs.players[player as usize].pawn_site;
    let region = gs.sites[site_idx as usize].region;
    let cost = if from_deck {
        search_deck_cost(gs, player)
    } else {
        2
    };
    gs.players[player as usize].supply -= cost;
    gs.supply_spent_this_turn += cost;

    // Draw count: default 3, Marshes (OATH-247) -1, Truthful Harp (OATH-214) +2
    let mut draw_count: i8 = 3;
    if gs.sites[site_idx as usize].site_id == SITE_MARSHES && gs.sites[site_idx as usize].is_faceup {
        draw_count -= 1;
    }
    let reveal_all = gs.players[player as usize].has_relic(RELIC_TRUTHFUL_HARP);
    if reveal_all {
        draw_count += 2;
    }
    draw_count += cards::denizens::search_draw_modifier(gs, player);
    let draw_count = draw_count.clamp(1, 6) as usize;

    let mut drawn: SmallVec<[CardId; 6]> = SmallVec::new();
    let mut actual_region = region;
    if from_deck {
        for _ in 0..draw_count {
            let Some(cid) = gs.world_deck.pop() else { break };
            drawn.push(cid);
            if get_card(cid).card_type == CardType::Vision {
                gs.visions_drawn = (gs.visions_drawn + 1).min(MAX_VISIONS_DRAWN);
                break; // §5.1.2 stop drawing immediately on Vision
            }
        }
    } else {
        if gs.discard_piles[region as usize].is_empty() && gs.player_has_card_access(player, 11) {
            if let Some(r) = (0..NUM_REGIONS).find(|&r| !gs.discard_piles[r].is_empty()) {
                actual_region = match r {
                    0 => Region::Cradle,
                    1 => Region::Provinces,
                    _ => Region::Hinterland,
                };
            }
        }
        for _ in 0..draw_count {
            let Some(cid) = gs.discard_piles[actual_region as usize].pop() else {
                break;
            };
            drawn.push(cid);
        }
    }

    if drawn.is_empty() {
        gs.actions_taken_this_turn += 1;
        return;
    }

    let remaining: SmallVec<[bool; 6]> = drawn.iter().map(|_| true).collect();
    gs.search = Some(SearchState {
        player,
        from_deck,
        discard_region: actual_region,
        drawn_cards: drawn,
        remaining,
        played_one: false,
        reveal_all,
    });
    gs.decision = DecisionPoint::SearchResolve { player };
    gs.actions_taken_this_turn += 1;
}

pub fn can_play_search_card(gs: &GameState, player: PlayerId, card_id: CardId, dest: u8) -> bool {
    let def = get_card(card_id);
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];

    // Ruined Temple (OATH-204): enemies of ruler cannot play Beast cards faceup
    if dest != 2 && def.suit == Some(Suit::Beast) && is_blocked_by_enemy_card(gs, player, EDIFICE_RUINED_TEMPLE) {
        return false;
    }

    match dest {
        // 0 = Play to Site
        0 => {
            if def.card_type != CardType::Denizen {
                return false;
            }
            if def.restriction == CardRestriction::AdviserOnly {
                return false;
            }
            let can_discard_full = site.site_id == SITE_GREAT_SLUM
                || gs.peoples_favor_holder == Some(player)
                || gs.player_has_card_access(player, 128); // Crop Rotation
            site.has_empty_slot() || (site.capacity > 0 && can_discard_full)
        }
        // 1 = Play as Faceup Adviser
        1 => {
            if def.card_type == CardType::Vision {
                return card_id == CARD_CONSPIRACY; // Conspiracy played faceup triggers immediately
            }
            if def.restriction == CardRestriction::SiteOnly {
                return false;
            }
            true
        }
        // 2 = Play as Facedown Adviser (blocked by enemy Gossip OATH-099)
        2 => !is_blocked_by_enemy_card(gs, player, 99),
        // 3 = Play as Revealed Vision (Exiles only, non-Conspiracy Visions)
        3 => {
            if def.card_type != CardType::Vision
                || card_id == CARD_CONSPIRACY
                || p.role != Role::Exile
            {
                return false;
            }
            // Vow of Obedience (121): cannot play Visions faceup
            if gs.player_has_card_access(player, 121) {
                return false;
            }
            // Secret Police (113): enemies cannot play Visions faceup at ruled site
            if is_blocked_by_enemy_card(gs, player, 113) {
                return false;
            }
            // Sacred Ground (174): cannot play Visions faceup unless pawn is at Sacred Ground's site
            if gs.sites.iter().any(|s| s.is_faceup && s.cards.contains(&174))
                && !site.cards.contains(&174)
            {
                return false;
            }
            true
        }
        _ => false,
    }
}

pub fn execute_search_play(gs: &mut GameState, player: PlayerId, card_idx: u8, dest: u8) {
    let Some(ref mut s) = gs.search else { return };
    if card_idx as usize >= s.drawn_cards.len() || !s.remaining[card_idx as usize] {
        return;
    }
    let cid = s.drawn_cards[card_idx as usize];
    s.remaining[card_idx as usize] = false;
    s.played_one = true;

    // Discard all remaining unplayed cards automatically per §5.1.3
    let remaining_cards: SmallVec<[CardId; 6]> = s
        .drawn_cards
        .iter()
        .enumerate()
        .filter(|(i, _)| s.remaining[*i])
        .map(|(_, &c)| c)
        .collect();
    let site_idx = gs.players[player as usize].pawn_site;
    let discard_dest_region = gs.sites[site_idx as usize].region.discard_target();
    let use_bottom = gs.players[player as usize].has_relic(RELIC_CRACKED_HORN);
    gs.search = None;

    for rem in remaining_cards {
        if let Some(suit) = get_card(rem).suit {
            gs.sites[site_idx as usize].suits_discarded_this_turn |= suit.bit();
        }
        if use_bottom {
            gs.world_deck.insert(0, rem);
        } else {
            gs.discard_piles[discard_dest_region as usize].push(rem);
        }
    }

    place_played_card(gs, player, cid, dest);
}

pub fn execute_search_discard(gs: &mut GameState, player: PlayerId, card_idx: u8) {
    let Some(ref mut s) = gs.search else { return };
    if card_idx as usize >= s.drawn_cards.len() || !s.remaining[card_idx as usize] {
        return;
    }
    let cid = s.drawn_cards[card_idx as usize];
    s.remaining[card_idx as usize] = false;
    let any_left = s.remaining.iter().any(|&r| r);

    let site_idx = gs.players[player as usize].pawn_site;
    if let Some(suit) = get_card(cid).suit {
        gs.sites[site_idx as usize].suits_discarded_this_turn |= suit.bit();
    }
    if gs.players[player as usize].has_relic(RELIC_CRACKED_HORN) {
        gs.world_deck.insert(0, cid);
    } else {
        let dest = gs.sites[site_idx as usize].region.discard_target();
        gs.discard_piles[dest as usize].push(cid);
    }

    if !any_left {
        gs.search = None;
        gs.decision = DecisionPoint::TurnAct { player };
    }
}

pub fn place_played_card(gs: &mut GameState, player: PlayerId, cid: CardId, dest: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    match dest {
        // Play to Site
        0 => {
            if let Some(slot) = gs.sites[site_idx as usize].first_empty_slot() {
                gs.sites[site_idx as usize].cards[slot] = cid;
                on_card_played_to_site(gs, player, site_idx, cid);
                gs.decision = DecisionPoint::TurnAct { player };
            } else {
                // Full site (Great Slum or People's Favor): choose slot to discard first
                let mut allowed = 0u8;
                let cap = gs.sites[site_idx as usize].capacity;
                for sl in 0..cap {
                    let existing = gs.sites[site_idx as usize].cards[sl as usize];
                    if get_card(existing).restriction != CardRestriction::Locked {
                        allowed |= 1u8 << sl;
                    }
                }
                if allowed == 0 {
                    // Fallback: discard played card
                    let dest_r = gs.sites[site_idx as usize].region.discard_target();
                    gs.discard_piles[dest_r as usize].push(cid);
                    gs.decision = DecisionPoint::TurnAct { player };
                } else {
                    gs.effect_stack.push(PendingEffect::ResumeSearchPlay {
                        player,
                        card_id: cid,
                        dest: 0,
                    });
                    gs.decision = DecisionPoint::ChooseSiteCard {
                        player,
                        site: site_idx,
                        reason: ChoiceReason::DiscardSiteCard,
                        allowed_slots: allowed,
                    };
                }
            }
        }
        // Play as Faceup Adviser (or Conspiracy)
        1 => {
            if cid == CARD_CONSPIRACY {
                resolve_conspiracy(gs, player);
                return;
            }
            if let Some(slot) = gs.players[player as usize].first_empty_adviser() {
                gs.players[player as usize].advisers[slot] = cid;
                gs.players[player as usize].adviser_faceup[slot] = true;
                cards::denizens::trigger_when_played(gs, player, cid);
                if matches!(gs.decision, DecisionPoint::SearchResolve { .. }) {
                    gs.decision = DecisionPoint::TurnAct { player };
                }
            } else {
                // Must discard an existing unlocked adviser first
                let mut allowed = 0u8;
                for sl in 0..MAX_ADVISERS {
                    if get_card(gs.players[player as usize].advisers[sl]).restriction
                        != CardRestriction::Locked
                    {
                        allowed |= 1u8 << sl;
                    }
                }
                if allowed == 0 {
                    let dest_r = gs.sites[site_idx as usize].region.discard_target();
                    gs.discard_piles[dest_r as usize].push(cid);
                    gs.decision = DecisionPoint::TurnAct { player };
                } else {
                    gs.effect_stack.push(PendingEffect::ResumeSearchPlay {
                        player,
                        card_id: cid,
                        dest: 1,
                    });
                    gs.decision = DecisionPoint::ChooseAdviser {
                        player,
                        owner: player,
                        reason: ChoiceReason::ReplaceAdviser,
                        allowed_slots: allowed,
                    };
                }
            }
        }
        // Play as Facedown Adviser
        2 => {
            if let Some(slot) = gs.players[player as usize].first_empty_adviser() {
                gs.players[player as usize].advisers[slot] = cid;
                gs.players[player as usize].adviser_faceup[slot] = false;
                for kb in &mut gs.knowledge {
                    kb.clear_adviser_known(player, slot);
                }
                gs.decision = DecisionPoint::TurnAct { player };
            } else {
                let mut allowed = 0u8;
                for sl in 0..MAX_ADVISERS {
                    if get_card(gs.players[player as usize].advisers[sl]).restriction
                        != CardRestriction::Locked
                    {
                        allowed |= 1u8 << sl;
                    }
                }
                if allowed == 0 {
                    let dest_r = gs.sites[site_idx as usize].region.discard_target();
                    gs.discard_piles[dest_r as usize].push(cid);
                    gs.decision = DecisionPoint::TurnAct { player };
                } else {
                    gs.effect_stack.push(PendingEffect::ResumeSearchPlay {
                        player,
                        card_id: cid,
                        dest: 2,
                    });
                    gs.decision = DecisionPoint::ChooseAdviser {
                        player,
                        owner: player,
                        reason: ChoiceReason::ReplaceAdviser,
                        allowed_slots: allowed,
                    };
                }
            }
        }
        // Play as Revealed Vision
        _ => {
            gs.players[player as usize].revealed_vision = Some(cid);
            gs.decision = DecisionPoint::TurnAct { player };
        }
    }
}

pub fn on_card_played_to_site(gs: &mut GameState, player: PlayerId, site_idx: SiteIndex, cid: CardId) {
    let def = get_card(cid);
    // Book of Records (OATH-229): must gain 1 secret instead of 1 favor when playing to site
    if gs.players[player as usize].has_relic(RELIC_BOOK_OF_RECORDS) {
        if gs.shared_secrets > 0 {
            gs.shared_secrets -= 1;
            gs.players[player as usize].secrets_faceup += 1;
        }
    } else if let Some(suit) = def.suit {
        if gs.favor_banks[suit as usize] > 0 {
            gs.favor_banks[suit as usize] -= 1;
            gs.players[player as usize].favor += 1;
        }
    }

    // Homeland / Search site powers (if suit not discarded here this turn)
    if let Some(suit) = def.suit {
        let discarded_mask = gs.sites[site_idx as usize].suits_discarded_this_turn;
        if (discarded_mask & suit.bit()) == 0 {
            let site_id = gs.sites[site_idx as usize].site_id;
            match (site_id, suit) {
                (SITE_ANCIENT_CITY, Suit::Order) => gain_warbands(gs, player, 2),
                (SITE_DEEP_WOODS, Suit::Beast) => {
                    if let Some(rid) = gs.sites[site_idx as usize].relics.pop() {
                        gs.players[player as usize].relics.push(rid);
                        recalculate_oathkeeper(gs);
                    }
                }
                (SITE_FERTILE_VALLEY, Suit::Hearth) => {
                    if gs.favor_banks[Suit::Hearth as usize] > 0 {
                        gs.favor_banks[Suit::Hearth as usize] -= 1;
                        gs.players[player as usize].favor += 1;
                    }
                }
                (SITE_STANDING_STONES, Suit::Arcane) => {
                    if gs.shared_secrets > 0 {
                        gs.shared_secrets -= 1;
                        gs.players[player as usize].secrets_faceup += 1;
                    }
                }
                (SITE_STEPPE, Suit::Nomad) => {
                    gs.players[player as usize].supply =
                        (gs.players[player as usize].supply + 1).min(MAX_SUPPLY);
                }
                (SITE_WASTES, Suit::Discord) => {
                    if gs.favor_banks[Suit::Discord as usize] > 0 {
                        gs.favor_banks[Suit::Discord as usize] -= 1;
                        gs.players[player as usize].favor += 1;
                    }
                }
                _ => {}
            }
        }
    }

    cards::denizens::trigger_when_played(gs, player, cid);
}

fn resolve_conspiracy(gs: &mut GameState, player: PlayerId) {
    // OATH-232 Conspiracy: burn 1 secret to take 1 relic/banner from player at same site
    // if you have >= 2 advisers matching any of their advisers. Return Conspiracy to box.
    if gs.players[player as usize].secrets_faceup > 0 {
        let my_site = gs.players[player as usize].pawn_site;
        for other in 0..gs.num_players {
            if other == player || gs.players[other as usize].pawn_site != my_site {
                continue;
            }
            if gs.players[other as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
                continue;
            }
            if count_matching_advisers(gs, player, other) >= 2 {
                // Take banner or relic
                if gs.peoples_favor_holder == Some(other) {
                    gs.players[player as usize].secrets_faceup -= 1;
                    gs.shared_secrets += 1;
                    seize_peoples_favor(gs, player);
                    gs.decision = DecisionPoint::TurnAct { player };
                    return;
                } else if gs.darkest_secret_holder == Some(other) {
                    gs.players[player as usize].secrets_faceup -= 1;
                    gs.shared_secrets += 1;
                    seize_darkest_secret(gs, player);
                    gs.decision = DecisionPoint::TurnAct { player };
                    return;
                } else if let Some(rid) = gs.players[other as usize].relics.pop() {
                    gs.players[player as usize].secrets_faceup -= 1;
                    gs.shared_secrets += 1;
                    if rid == CARD_GRAND_SCEPTER {
                        gs.scepter_taken_this_turn = true;
                    }
                    gs.players[player as usize].relics.push(rid);
                    recalculate_oathkeeper(gs);
                    gs.decision = DecisionPoint::TurnAct { player };
                    return;
                }
            }
        }
    }
    gs.decision = DecisionPoint::TurnAct { player };
}

fn count_matching_advisers(gs: &GameState, p1: PlayerId, p2: PlayerId) -> u8 {
    let mut suits2 = 0u8;
    for sl in 0..MAX_ADVISERS {
        let c = gs.players[p2 as usize].advisers[sl];
        if c != CARD_EMPTY && gs.players[p2 as usize].adviser_faceup[sl] {
            if let Some(s) = get_card(c).suit {
                suits2 |= s.bit();
            }
        }
    }
    let mut matches = 0u8;
    for sl in 0..MAX_ADVISERS {
        let c = gs.players[p1 as usize].advisers[sl];
        if c != CARD_EMPTY && gs.players[p1 as usize].adviser_faceup[sl] {
            if let Some(s) = get_card(c).suit {
                if (suits2 & s.bit()) != 0 {
                    matches += 1;
                }
            }
        }
    }
    matches
}

// ── RECOVER (§5.4) ────────────────────────────────────────────────────────

pub fn can_recover_relic(gs: &GameState, player: PlayerId, relic_slot: u8) -> bool {
    let p = &gs.players[player as usize];
    if p.supply < 1 {
        return false;
    }
    let site = &gs.sites[p.pawn_site as usize];
    if !site.is_faceup || relic_slot as usize >= site.relics.len() {
        return false;
    }
    let def = get_card(site.site_id);
    p.favor >= def.recover_favor && p.secrets_faceup >= def.recover_secrets
}

pub fn execute_recover_relic(gs: &mut GameState, player: PlayerId, relic_slot: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let def = get_card(gs.sites[site_idx as usize].site_id);
    gs.players[player as usize].supply -= 1;
    gs.supply_spent_this_turn += 1;
    if def.recover_favor > 0 {
        gs.players[player as usize].favor -= def.recover_favor;
        let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
        gs.favor_banks[min_i] += def.recover_favor;
    }
    if def.recover_secrets > 0 {
        gs.players[player as usize].secrets_faceup -= def.recover_secrets;
        gs.shared_secrets += def.recover_secrets;
    }
    let rid = gs.sites[site_idx as usize].relics.remove(relic_slot as usize);
    gs.players[player as usize].relics.push(rid);
    // Relic Worship (OATH-173): after recovering a relic, gain 3 Supply
    if gs.player_has_card_access(player, 173) {
        gs.players[player as usize].supply =
            (gs.players[player as usize].supply + 3).min(MAX_SUPPLY);
    }
    recalculate_oathkeeper(gs);
    gs.actions_taken_this_turn += 1;
}

pub fn can_recover_peoples_favor(gs: &GameState, player: PlayerId) -> bool {
    let p = &gs.players[player as usize];
    if p.supply < 1 {
        return false;
    }
    // Vow of Renewal (OATH-086): cannot recover People's Favor
    if gs.player_has_card_access(player, 86) {
        return false;
    }
    if check_contract_violation_banner(gs, player, Banner::PeoplesFavor) {
        return false;
    }
    if let Some(holder) = gs.peoples_favor_holder {
        if holder != player {
            if gs.players[holder as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
                return false;
            }
            if gs.player_has_card_access(holder, 157)
                && !cards::denizens::player_rules_suit(gs, player, Suit::Nomad)
            {
                return false;
            }
        }
    }
    p.favor > gs.peoples_favor_tokens
}

pub fn execute_recover_peoples_favor(gs: &mut GameState, player: PlayerId) {
    gs.players[player as usize].supply -= 1;
    gs.supply_spent_this_turn += 1;
    let cost = gs.peoples_favor_tokens + 1;
    let old_tokens = gs.peoples_favor_tokens;
    let prev_holder = gs.peoples_favor_holder;

    gs.players[player as usize].favor -= cost;
    gs.peoples_favor_holder = Some(player);
    gs.peoples_favor_tokens = cost;

    // Redistribute old tokens: 1 to prev holder (if any), rest to smallest favor banks
    let mut to_banks = old_tokens;
    if let Some(prev) = prev_holder {
        if prev != player && to_banks > 0 {
            gs.players[prev as usize].favor += 1;
            to_banks -= 1;
        }
    }
    for _ in 0..to_banks {
        let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
        gs.favor_banks[min_i] += 1;
    }

    // Hall of Mockery (OATH-202): always flips PF to Mob side
    let has_hall_of_mockery = gs
        .sites
        .iter()
        .any(|s| s.is_faceup && s.cards.contains(&EDIFICE_HALL_OF_MOCKERY));
    if gs.peoples_favor_tokens >= 6 || has_hall_of_mockery {
        gs.peoples_favor_is_mob = true;
    }

    recalculate_oathkeeper(gs);
    gs.actions_taken_this_turn += 1;
}

pub fn can_recover_darkest_secret(gs: &GameState, player: PlayerId) -> bool {
    let p = &gs.players[player as usize];
    if p.supply < 1 {
        return false;
    }
    // Vow of Silence (OATH-074): cannot recover Darkest Secret
    if gs.player_has_card_access(player, 74) {
        return false;
    }
    // Tome Guardians (OATH-110): enemies cannot recover Darkest Secret
    if is_blocked_by_enemy_card(gs, player, 110) {
        return false;
    }
    if check_contract_violation_banner(gs, player, Banner::DarkestSecret) {
        return false;
    }
    // Magician's Code (OATH-032): +2 secrets toward recovering Darkest Secret
    let bonus = if gs.player_has_card_access(player, 32) { 2 } else { 0 };
    if p.secrets_faceup + bonus <= gs.darkest_secret_tokens {
        return false;
    }
    if let Some(holder) = gs.darkest_secret_holder {
        if holder != player {
            if gs.players[holder as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
                return false;
            }
            if gs.player_has_card_access(holder, 157)
                && !cards::denizens::player_rules_suit(gs, player, Suit::Nomad)
            {
                return false;
            }
            let holder_has_faceup = (0..MAX_ADVISERS).any(|sl| {
                gs.players[holder as usize].advisers[sl] != CARD_EMPTY
                    && gs.players[holder as usize].adviser_faceup[sl]
            });
            if !holder_has_faceup {
                return false;
            }
        }
    }
    true
}

pub fn execute_recover_darkest_secret(gs: &mut GameState, player: PlayerId) {
    gs.players[player as usize].supply -= 1;
    gs.supply_spent_this_turn += 1;
    let cost = gs.darkest_secret_tokens + 1;
    let old_tokens = gs.darkest_secret_tokens;
    let prev_holder = gs.darkest_secret_holder;

    let discount = if gs.player_has_card_access(player, 32) {
        let g = 2.min(gs.shared_secrets);
        gs.shared_secrets -= g;
        g
    } else {
        0
    };
    let pay_from_board = cost.saturating_sub(discount).min(gs.players[player as usize].secrets_faceup);
    gs.players[player as usize].secrets_faceup -= pay_from_board;
    gs.darkest_secret_holder = Some(player);
    gs.darkest_secret_tokens = pay_from_board + discount;

    // Vow of Silence (OATH-074): whenever a player recovers DS, holder of Vow of Silence gains X secrets
    for o in 0..gs.num_players {
        if o != player && gs.player_has_card_access(o, 74) {
            let g = gs.darkest_secret_tokens.min(gs.shared_secrets);
            gs.shared_secrets -= g;
            gs.players[o as usize].secrets_faceup += g;
        }
    }

    // §5.4.4: new holder takes 1 secret, prev holder gets rest (or shared bank)
    if old_tokens > 0 {
        gs.players[player as usize].secrets_faceup += 1;
        let rest = old_tokens - 1;
        if let Some(prev) = prev_holder {
            if prev != player {
                gs.players[prev as usize].secrets_faceup += rest;
            } else {
                gs.shared_secrets += rest;
            }
        } else {
            gs.shared_secrets += rest;
        }
    }

    recalculate_oathkeeper(gs);
    gs.actions_taken_this_turn += 1;
}

/// Seize People's Favor via Campaign or Conspiracy (§2.5.3): burn 2 favor (min 1), flip to Mob.
pub fn seize_peoples_favor(gs: &mut GameState, new_holder: PlayerId) {
    let burn = gs.peoples_favor_tokens.saturating_sub(1).min(2);
    gs.peoples_favor_tokens -= burn;
    for _ in 0..burn {
        let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
        gs.favor_banks[min_i] += 1;
    }
    gs.peoples_favor_holder = Some(new_holder);
    gs.peoples_favor_is_mob = true;
    recalculate_oathkeeper(gs);
}

/// Seize Darkest Secret via Campaign or Conspiracy: burn 2 secrets (min 1).
pub fn seize_darkest_secret(gs: &mut GameState, new_holder: PlayerId) {
    let burn = gs.darkest_secret_tokens.saturating_sub(1).min(2);
    gs.darkest_secret_tokens -= burn;
    gs.shared_secrets += burn;
    gs.darkest_secret_holder = Some(new_holder);
    recalculate_oathkeeper(gs);
}

// ── Shared Helpers ────────────────────────────────────────────────────────

pub fn warband_bank_for(gs: &GameState, player: PlayerId) -> u8 {
    if gs.players[player as usize].role == Role::Citizen {
        let c = gs.chancellor_index();
        gs.players[c as usize].warbands_bank
    } else {
        gs.players[player as usize].warbands_bank
    }
}

pub fn gain_warbands(gs: &mut GameState, player: PlayerId, amount: u8) {
    if gs.players[player as usize].role == Role::Citizen {
        let c = gs.chancellor_index();
        let actual = amount.min(gs.players[c as usize].warbands_bank);
        gs.players[c as usize].warbands_bank -= actual;
        gs.players[player as usize].warbands_board += actual;
    } else {
        let actual = amount.min(gs.players[player as usize].warbands_bank);
        gs.players[player as usize].warbands_bank -= actual;
        gs.players[player as usize].warbands_board += actual;
    }
}

pub fn kill_warbands_from_board(gs: &mut GameState, player: PlayerId, amount: u8) -> u8 {
    let actual = amount.min(gs.players[player as usize].warbands_board);
    gs.players[player as usize].warbands_board -= actual;
    if gs.players[player as usize].role == Role::Citizen {
        let c = gs.chancellor_index();
        gs.players[c as usize].warbands_bank += actual;
    } else {
        gs.players[player as usize].warbands_bank += actual;
    }
    actual
}

pub fn is_blocked_by_enemy_card(gs: &GameState, player: PlayerId, card_id: CardId) -> bool {
    for si in 0..MAX_SITES as u8 {
        let s = &gs.sites[si as usize];
        if s.is_faceup && s.cards[..s.capacity as usize].contains(&card_id) {
            if let Some(ruler) = s.ruling_player {
                if ruler != player && !(gs.is_imperial(player) && gs.is_imperial(ruler)) {
                    return true;
                }
            }
        }
    }
    for p in 0..gs.num_players {
        if p == player || (gs.is_imperial(player) && gs.is_imperial(p)) {
            continue;
        }
        for sl in 0..MAX_ADVISERS {
            if gs.players[p as usize].advisers[sl] == card_id
                && gs.players[p as usize].adviser_faceup[sl]
            {
                return true;
            }
        }
    }
    false
}

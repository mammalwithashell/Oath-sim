use crate::cards::{self, get_card};
use crate::engine::deals::start_deal;
use crate::engine::turn::calculate_base_supply;
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

// ── FLIP / DISCARD ADVISER (§6.1) ─────────────────────────────────────────

pub fn can_flip_adviser(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    if slot as usize >= MAX_ADVISERS {
        return false;
    }
    let p = &gs.players[player as usize];
    let cid = p.advisers[slot as usize];
    if cid == CARD_EMPTY || p.adviser_faceup[slot as usize] {
        return false;
    }
    let def = get_card(cid);
    if def.card_type == CardType::Vision {
        return cid == CARD_CONSPIRACY || p.role == Role::Exile;
    }
    def.restriction != CardRestriction::SiteOnly
}

pub fn execute_flip_adviser(gs: &mut GameState, player: PlayerId, slot: u8) {
    let cid = gs.players[player as usize].advisers[slot as usize];
    if get_card(cid).card_type == CardType::Vision {
        gs.players[player as usize].advisers[slot as usize] = CARD_EMPTY;
        gs.players[player as usize].adviser_faceup[slot as usize] = false;
        if cid == CARD_CONSPIRACY {
            crate::engine::major_actions::place_played_card(gs, player, cid, 1);
        } else {
            gs.players[player as usize].revealed_vision = Some(cid);
        }
        return;
    }
    gs.players[player as usize].adviser_faceup[slot as usize] = true;
    cards::denizens::trigger_when_played(gs, player, cid);
}

pub fn can_discard_adviser(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    if slot as usize >= MAX_ADVISERS {
        return false;
    }
    let p = &gs.players[player as usize];
    let cid = p.advisers[slot as usize];
    if cid == CARD_EMPTY {
        return false;
    }
    !(p.adviser_faceup[slot as usize] && get_card(cid).restriction == CardRestriction::Locked)
}

pub fn execute_discard_adviser(gs: &mut GameState, player: PlayerId, slot: u8) {
    let cid = gs.players[player as usize].advisers[slot as usize];
    gs.players[player as usize].advisers[slot as usize] = CARD_EMPTY;
    gs.players[player as usize].adviser_faceup[slot as usize] = false;
    for kb in &mut gs.knowledge {
        kb.clear_adviser_known(player, slot as usize);
    }
    let site_idx = gs.players[player as usize].pawn_site;
    let dest = gs.sites[site_idx as usize].region.discard_target();
    gs.discard_piles[dest as usize].push(cid);
}

// ── PEEK RELIC / RELIQUARY (§6.3, §6.4) ───────────────────────────────────

pub fn can_peek_site_relic(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    let site_idx = gs.players[player as usize].pawn_site;
    let site = &gs.sites[site_idx as usize];
    site.is_faceup
        && (slot as usize) < site.relics.len()
        && !gs.knowledge[player as usize].knows_site_relic(site_idx, slot as usize)
}

pub fn execute_peek_site_relic(gs: &mut GameState, player: PlayerId, slot: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    gs.knowledge[player as usize].mark_site_relic_known(site_idx, slot as usize);
}

pub fn can_peek_reliquary(gs: &GameState, player: PlayerId) -> bool {
    if !gs.players[player as usize].has_relic(CARD_GRAND_SCEPTER) || gs.scepter_taken_this_turn {
        return false;
    }
    (0..gs.reliquary.len()).any(|sl| !gs.knowledge[player as usize].knows_reliquary(sl))
}

pub fn execute_peek_reliquary(gs: &mut GameState, player: PlayerId) {
    for sl in 0..gs.reliquary.len() {
        gs.knowledge[player as usize].mark_reliquary_known(sl);
    }
}

// ── MOVE WARBANDS (§6.5) ──────────────────────────────────────────────────

pub fn can_move_warbands_to_board(gs: &GameState, player: PlayerId) -> bool {
    let site_idx = gs.players[player as usize].pawn_site;
    if !gs.player_rules_site(player, site_idx) {
        return false;
    }
    let site = &gs.sites[site_idx as usize];
    // Cannot move last warband off site, and Bandit Crown bandits cannot be moved
    site.warbands > 1
}

pub fn execute_move_warbands_to_board(gs: &mut GameState, player: PlayerId, amount: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let avail = gs.sites[site_idx as usize].warbands.saturating_sub(1);
    let moved = amount.min(avail);
    gs.sites[site_idx as usize].warbands -= moved;
    gs.players[player as usize].warbands_board += moved;
}

pub fn can_move_warbands_to_site(gs: &GameState, player: PlayerId) -> bool {
    let p = &gs.players[player as usize];
    if p.has_relic(RELIC_RING_OF_DEVOTION) {
        return false; // OATH-222: cannot place warbands at sites
    }
    let site_idx = p.pawn_site;
    gs.player_rules_site(player, site_idx) && p.warbands_board > 0 && gs.sites[site_idx as usize].warbands > 0
}

pub fn execute_move_warbands_to_site(gs: &mut GameState, player: PlayerId, amount: u8) {
    let site_idx = gs.players[player as usize].pawn_site;
    let moved = amount.min(gs.players[player as usize].warbands_board);
    gs.players[player as usize].warbands_board -= moved;
    gs.sites[site_idx as usize].warbands += moved;
}

// ── CITIZENSHIP & EXILING (§6.6, §6.7, §6.8) ──────────────────────────────

pub fn can_offer_citizenship(gs: &GameState, player: PlayerId, target: PlayerId) -> bool {
    if target == player || target >= gs.num_players {
        return false;
    }
    if !gs.players[player as usize].has_relic(CARD_GRAND_SCEPTER) || gs.scepter_taken_this_turn {
        return false;
    }
    if gs.reliquary.is_empty() {
        return false;
    }
    gs.players[target as usize].role == Role::Exile
}

pub fn execute_offer_citizenship(gs: &mut GameState, player: PlayerId, target: PlayerId) {
    start_deal(gs, DealKind::Citizenship, player, target);
}

pub fn exile_citizen_cost(gs: &GameState, player: PlayerId, target: PlayerId) -> u8 {
    let mut cost: i8 = 5;
    if gs.oathkeeper_holder == Some(player) {
        cost -= 1;
    }
    if gs.peoples_favor_holder == Some(player) {
        cost -= 1;
    }
    if gs.oathkeeper_holder == Some(target) {
        cost += 2;
    }
    if gs.peoples_favor_holder == Some(target) {
        cost += 2;
    }
    cost.max(0) as u8
}

pub fn can_exile_citizen(gs: &GameState, player: PlayerId, target: PlayerId) -> bool {
    if target == player || target >= gs.num_players {
        return false;
    }
    if !gs.players[player as usize].has_relic(CARD_GRAND_SCEPTER) || gs.scepter_taken_this_turn {
        return false;
    }
    if gs.players[target as usize].role != Role::Citizen {
        return false;
    }
    // Council Seat (OATH-123): Citizen cannot be exiled
    if gs.player_has_card_access(target, 123) {
        return false;
    }
    gs.players[player as usize].favor >= exile_citizen_cost(gs, player, target)
}

pub fn execute_exile_citizen(gs: &mut GameState, player: PlayerId, target: PlayerId) {
    let cost = exile_citizen_cost(gs, player, target);
    gs.players[player as usize].favor -= cost;
    for _ in 0..cost {
        let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
        gs.favor_banks[min_i] += 1;
    }
    convert_citizen_to_exile(gs, target);
}

pub fn self_exile_cost(gs: &GameState, player: PlayerId) -> u8 {
    let p = &gs.players[player as usize];
    p.total_secrets() + p.warbands_board
}

pub fn can_self_exile(gs: &GameState, player: PlayerId) -> bool {
    let p = &gs.players[player as usize];
    if gs.player_has_card_access(player, 123) {
        return false; // Council Seat (OATH-123)
    }
    p.role == Role::Citizen
        && !p.has_relic(CARD_GRAND_SCEPTER)
        && p.favor >= self_exile_cost(gs, player)
}

pub fn execute_self_exile(gs: &mut GameState, player: PlayerId) {
    let cost = self_exile_cost(gs, player);
    gs.players[player as usize].favor -= cost;
    // Pay to Grand Scepter holder
    let scepter_holder = (0..gs.num_players)
        .find(|&p| gs.players[p as usize].has_relic(CARD_GRAND_SCEPTER))
        .unwrap_or(gs.chancellor_index());
    gs.players[scepter_holder as usize].favor += cost;
    convert_citizen_to_exile(gs, player);
    // Self-exile ends Act Phase (§6.8)
    crate::engine::turn::do_rest_phase(gs);
}

pub fn convert_citizen_to_exile(gs: &mut GameState, target: PlayerId) {
    let chanc = gs.chancellor_index();
    let board_wb = gs.players[target as usize].warbands_board;
    // Return purple warbands to Chancellor's bank, replace with Exile's own warbands
    gs.players[chanc as usize].warbands_bank =
        (gs.players[chanc as usize].warbands_bank + board_wb).min(MAX_WARBANDS_CHANCELLOR);
    gs.players[target as usize].role = Role::Exile;
    let take_own = board_wb.min(MAX_WARBANDS_EXILE);
    gs.players[target as usize].warbands_board = take_own;
    gs.players[target as usize].warbands_bank = MAX_WARBANDS_EXILE - take_own;
    gs.players[target as usize].supply = calculate_base_supply(gs, target);
    recalculate_oathkeeper(gs);
}

pub fn convert_exile_to_citizen(gs: &mut GameState, target: PlayerId) {
    let chanc = gs.chancellor_index();
    let old_board = gs.players[target as usize].warbands_board;
    // Replace Exile warbands at sites with purple (up to Chancellor bank)
    for si in 0..MAX_SITES {
        if gs.sites[si].ruling_player == Some(target) && gs.sites[si].warband_color == Some(target) {
            let wb = gs.sites[si].warbands;
            let purple = wb.min(gs.players[chanc as usize].warbands_bank);
            gs.players[chanc as usize].warbands_bank -= purple;
            gs.sites[si].warbands = purple;
            gs.sites[si].warband_color = Some(0);
            if purple == 0 {
                gs.sites[si].ruling_player = None;
                gs.sites[si].warband_color = None;
            }
        }
    }
    let purple_board = old_board.min(gs.players[chanc as usize].warbands_bank);
    gs.players[chanc as usize].warbands_bank -= purple_board;
    gs.players[target as usize].warbands_board = purple_board;
    gs.players[target as usize].warbands_bank = 0;
    gs.players[target as usize].role = Role::Citizen;
    gs.players[target as usize].revealed_vision = None; // §6.6.2 discard revealed vision
    if gs.oathkeeper_holder == Some(target) {
        gs.oathkeeper_side = TitleSide::Oathkeeper;
    }
    gs.players[target as usize].supply = calculate_base_supply(gs, target);
    recalculate_oathkeeper(gs);
}

// ── CARD ACTION POWERS (§6.2, §7.3.2) ─────────────────────────────────────

pub fn resolve_action_slot_card(gs: &GameState, player: PlayerId, slot: u8) -> Option<CardId> {
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];
    match slot {
        0..=2 => {
            if site.is_faceup && slot < site.capacity && site.cards[slot as usize] != CARD_EMPTY {
                Some(site.cards[slot as usize])
            } else {
                None
            }
        }
        3..=5 => {
            let adv_idx = (slot - 3) as usize;
            if p.advisers[adv_idx] != CARD_EMPTY && p.adviser_faceup[adv_idx] {
                Some(p.advisers[adv_idx])
            } else {
                None
            }
        }
        6 => {
            if site.is_faceup {
                Some(site.site_id)
            } else {
                None
            }
        }
        7..=10 => p.relics.get((slot - 7) as usize).copied(),
        _ => None,
    }
}

pub fn can_use_card_action(gs: &GameState, player: PlayerId, slot: u8) -> bool {
    let Some(cid) = resolve_action_slot_card(gs, player, slot) else {
        return false;
    };
    if gs.used_card_powers_this_turn.contains(&cid) {
        return false;
    }
    let def = get_card(cid);
    let p = &gs.players[player as usize];
    if p.favor < def.cost_favor + def.cost_burn_favor
        || p.secrets_faceup < def.cost_secrets + def.cost_burn_secrets
    {
        return false;
    }
    // Spell Breaker (OATH-162): enemies cannot use powers costing secrets
    if (def.cost_secrets > 0 || def.cost_burn_secrets > 0)
        && crate::engine::major_actions::is_blocked_by_enemy_card(gs, player, 162)
    {
        return false;
    }
    match def.card_type {
        CardType::Site => cards::sites::can_use_site_action(gs, player, cid),
        CardType::Relic => cards::relics::can_use_relic_action(gs, player, cid),
        CardType::Edifice => cards::edifices::can_use_edifice_action(gs, player, cid),
        CardType::Denizen => cards::denizens::can_use_denizen_action(gs, player, cid),
        _ => false,
    }
}

pub fn execute_use_card_action(gs: &mut GameState, player: PlayerId, slot: u8) {
    let Some(cid) = resolve_action_slot_card(gs, player, slot) else {
        return;
    };
    gs.used_card_powers_this_turn.push(cid);
    let def = get_card(cid);
    // Pay standard burn/spend costs
    if def.cost_burn_favor > 0 {
        gs.players[player as usize].favor -= def.cost_burn_favor;
        let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
        gs.favor_banks[min_i] += def.cost_burn_favor;
    }
    if def.cost_burn_secrets > 0 {
        gs.players[player as usize].secrets_faceup -= def.cost_burn_secrets;
        gs.shared_secrets += def.cost_burn_secrets;
    }
    if def.cost_favor > 0 {
        gs.players[player as usize].favor -= def.cost_favor;
        if slot <= 2 {
            let si = gs.players[player as usize].pawn_site as usize;
            gs.sites[si].card_favor[slot as usize] += def.cost_favor;
        } else {
            let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
            gs.favor_banks[min_i] += def.cost_favor;
        }
    }
    if def.cost_secrets > 0 {
        gs.players[player as usize].secrets_faceup -= def.cost_secrets;
        if slot <= 2 {
            let si = gs.players[player as usize].pawn_site as usize;
            gs.sites[si].card_secrets[slot as usize] += def.cost_secrets;
        } else {
            gs.shared_secrets += def.cost_secrets;
        }
    }

    match def.card_type {
        CardType::Site => cards::sites::execute_site_action(gs, player, cid),
        CardType::Relic => cards::relics::execute_relic_action(gs, player, cid),
        CardType::Edifice => cards::edifices::execute_edifice_action(gs, player, cid),
        CardType::Denizen => cards::denizens::execute_denizen_action(gs, player, cid),
        _ => {}
    }
}

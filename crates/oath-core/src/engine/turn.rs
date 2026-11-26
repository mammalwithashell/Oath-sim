use crate::cards;
use crate::engine::deals::check_contract_deadlines;
use crate::engine::win::{check_start_of_turn_wins, recalculate_oathkeeper, resolve_end_of_round_roll};
use crate::state::*;
use crate::types::*;

/// Begin the current player's turn (Wake Phase §4.1).
pub fn start_turn(gs: &mut GameState) {
    let p = gs.current_player;
    gs.phase = Phase::Wake;
    gs.supply_spent_this_turn = 0;
    gs.actions_taken_this_turn = 0;
    gs.scepter_taken_this_turn = false;
    gs.used_card_powers_this_turn.clear();
    gs.players[p as usize].talk_remaining = MAX_TALK_PER_TURN;
    for s in &mut gs.sites {
        s.suits_discarded_this_turn = 0;
    }
    resume_wake_phase(gs, p, 0);
}

/// Step-based Wake Phase (§4.1) that pauses for interactive choices (PF bank tie, site wake, Wake cards).
pub fn resume_wake_phase(gs: &mut GameState, player: PlayerId, step: u8) {
    if gs.is_game_over || gs.phase == Phase::Chronicle {
        return;
    }

    match step {
        // Step 0: People's Favor Wake Power (§4.1.1)
        0 => {
            if gs.peoples_favor_holder == Some(player) {
                let times = if gs.peoples_favor_is_mob { 2 } else { 1 };
                for _ in 0..times {
                    resolve_peoples_favor_tick(gs);
                }
                if gs.peoples_favor_tokens >= 6 {
                    gs.peoples_favor_is_mob = true;
                } else {
                    gs.peoples_favor_is_mob = false;
                }
            }
            resume_wake_phase(gs, player, 1);
        }
        // Step 1: Check Usurper / Visionary Wins (§4.1.2)
        1 => {
            if check_start_of_turn_wins(gs, player) {
                return;
            }
            resume_wake_phase(gs, player, 2);
        }
        // Step 2: Flip Oathkeeper to Usurper if Exile (§4.1.3)
        2 => {
            if gs.players[player as usize].role == Role::Exile
                && gs.oathkeeper_holder == Some(player)
                && gs.oathkeeper_side == TitleSide::Oathkeeper
            {
                gs.oathkeeper_side = TitleSide::Usurper;
            }
            resume_wake_phase(gs, player, 3);
        }
        // Step 3: Site Wake Power (§4.1.4) — Drowned City, Mine, Salt Flats
        3 => {
            let site_idx = gs.players[player as usize].pawn_site;
            let site_id = gs.sites[site_idx as usize].site_id;
            match site_id {
                SITE_DROWNED_CITY => {
                    if gs.sites[site_idx as usize].site_secrets > 0 {
                        gs.sites[site_idx as usize].site_secrets -= 1;
                        gs.players[player as usize].secrets_faceup += 1;
                    }
                    resume_wake_phase(gs, player, 4);
                }
                SITE_MINE => {
                    if gs.sites[site_idx as usize].site_favor > 0 {
                        gs.sites[site_idx as usize].site_favor -= 1;
                        gs.players[player as usize].favor += 1;
                    }
                    resume_wake_phase(gs, player, 4);
                }
                SITE_SALT_FLATS => {
                    let has_fav = gs.sites[site_idx as usize].site_favor > 0;
                    let has_sec = gs.sites[site_idx as usize].site_secrets > 0;
                    if has_fav && has_sec {
                        // Let player choose: Confirm = Secret, Decline = Favor
                        gs.effect_stack
                            .push(PendingEffect::ResumeWakePhase { player, step: 4 });
                        gs.decision = DecisionPoint::ChooseYesNo {
                            player,
                            reason: ChoiceReason::SiteWakeResource,
                            source_card: SITE_SALT_FLATS,
                        };
                        return;
                    } else if has_sec {
                        gs.sites[site_idx as usize].site_secrets -= 1;
                        gs.players[player as usize].secrets_faceup += 1;
                    } else if has_fav {
                        gs.sites[site_idx as usize].site_favor -= 1;
                        gs.players[player as usize].favor += 1;
                    }
                    resume_wake_phase(gs, player, 4);
                }
                _ => resume_wake_phase(gs, player, 4),
            }
        }
        // Step 4: Card Wake powers (§7.3.1)
        4 => {
            cards::denizens::trigger_wake_powers(gs, player);
            resume_wake_phase(gs, player, 5);
        }
        // Step 5: Transition to Act Phase
        _ => {
            gs.phase = Phase::Act;
            gs.decision = DecisionPoint::TurnAct { player };
        }
    }
}

/// People's Favor wake tick: take 1 favor from bank with most or place 1 to bank with least (§4.1.1).
fn resolve_peoples_favor_tick(gs: &mut GameState) {
    // Standard rule: place 1 favor from People's Favor onto a favor bank with least favor
    // if PF has > 1 token, or draw 1 from bank with most if desired. Keep PF >= 1.
    if gs.peoples_favor_tokens > 1 {
        let min_val = *gs.favor_banks.iter().min().unwrap_or(&0);
        if let Some(idx) = gs.favor_banks.iter().position(|&v| v == min_val) {
            gs.peoples_favor_tokens -= 1;
            gs.favor_banks[idx] += 1;
        }
    } else {
        let max_val = *gs.favor_banks.iter().max().unwrap_or(&0);
        if max_val > 0 {
            if let Some(idx) = gs.favor_banks.iter().position(|&v| v == max_val) {
                gs.favor_banks[idx] -= 1;
                gs.peoples_favor_tokens += 1;
            }
        }
    }
}

/// Execute Rest Phase (§4.3) and advance to next player or End-of-Round.
pub fn do_rest_phase(gs: &mut GameState) {
    let player = gs.current_player;
    gs.phase = Phase::Rest;

    // 1. Return Favor on denizens/edifices to matching suit favor banks (§4.3.1)
    for si in 0..MAX_SITES {
        let cap = gs.sites[si].capacity as usize;
        for slot in 0..cap {
            let fav = gs.sites[si].card_favor[slot];
            if fav > 0 {
                let cid = gs.sites[si].cards[slot];
                gs.sites[si].card_favor[slot] = 0;
                if let Some(suit) = cards::get_card(cid).suit {
                    gs.favor_banks[suit as usize] += fav;
                } else {
                    gs.favor_banks[0] += fav;
                }
            }
        }
    }

    // 2. Return Secrets on denizens/edifices to current player's board & flip facedown secrets faceup (§4.3.2)
    let mut returned_secrets = 0u8;
    for si in 0..MAX_SITES {
        let cap = gs.sites[si].capacity as usize;
        for slot in 0..cap {
            let sec = gs.sites[si].card_secrets[slot];
            if sec > 0 {
                gs.sites[si].card_secrets[slot] = 0;
                returned_secrets += sec;
            }
        }
    }
    let p = &mut gs.players[player as usize];
    p.secrets_faceup += returned_secrets + p.secrets_facedown;
    p.secrets_facedown = 0;

    // 3. Refresh Supply (§4.3.3) + 4. Save Supply (§4.3.4)
    let unspent = p.supply;
    let base_supply = calculate_base_supply(gs, player);
    gs.players[player as usize].supply = (base_supply + unspent).min(MAX_SUPPLY);

    // 5. Rest card powers (§4.3.5)
    cards::denizens::trigger_rest_powers(gs, player);

    // Check Tribunal MustCampaign contract deadlines
    check_contract_deadlines(gs, player);

    // Recalculate Oathkeeper
    recalculate_oathkeeper(gs);

    // Advance turn
    advance_turn(gs);
}

pub fn calculate_base_supply(gs: &GameState, player: PlayerId) -> u8 {
    let p = &gs.players[player as usize];
    if p.role == Role::Citizen {
        let chanc = gs.chancellor_index();
        return supply_from_bank(gs.players[chanc as usize].warbands_bank, true);
    }
    supply_from_bank(p.warbands_bank, p.role == Role::Chancellor)
}

/// Official Oath supply track mapping from warbands remaining in personal bank.
pub fn supply_from_bank(bank: u8, is_chancellor: bool) -> u8 {
    if is_chancellor {
        match bank {
            19..=24 => 7,
            13..=18 => 6,
            8..=12 => 5,
            4..=7 => 4,
            1..=3 => 3,
            0 => 2,
            _ => 7,
        }
    } else {
        match bank {
            11..=14 => 7,
            8..=10 => 6,
            5..=7 => 5,
            3..=4 => 4,
            1..=2 => 3,
            0 => 2,
            _ => 7,
        }
    }
}

pub fn advance_turn(gs: &mut GameState) {
    if gs.is_game_over || gs.phase == Phase::Chronicle {
        return;
    }

    gs.turn_in_round += 1;
    if gs.turn_in_round >= gs.num_players {
        // End of round!
        gs.turn_in_round = 0;
        handle_end_of_round(gs);
    } else {
        gs.current_player = gs.turn_order[gs.turn_in_round as usize];
        start_turn(gs);
    }
}

fn handle_end_of_round(gs: &mut GameState) {
    recalculate_oathkeeper(gs);

    if gs.round_number >= 5 {
        let roll = gs.rng.gen_range_u8(6) + 1; // 1..=6

        // Squalid District (OATH-206): ruler (if not Citizen) may +/- 1 to end die roll
        if gs.round_number < MAX_ROUNDS {
            if let Some(ruler) = find_card_ruler(gs, EDIFICE_SQUALID_DISTRICT) {
                if gs.players[ruler as usize].role != Role::Citizen {
                    gs.effect_stack
                        .push(PendingEffect::ResumeEndOfRoundCheck { roll });
                    gs.decision = DecisionPoint::ChooseYesNo {
                        player: ruler,
                        reason: ChoiceReason::SqualidDistrictRoll,
                        source_card: EDIFICE_SQUALID_DISTRICT,
                    };
                    return;
                }
            }
        }

        finish_end_of_round(gs, roll);
    } else {
        gs.round_number += 1;
        gs.current_player = gs.turn_order[0];
        start_turn(gs);
    }
}

pub fn finish_end_of_round(gs: &mut GameState, roll: u8) {
    if resolve_end_of_round_roll(gs, roll) {
        return;
    }
    gs.round_number += 1;
    gs.current_player = gs.turn_order[0];
    start_turn(gs);
}

pub fn find_card_ruler(gs: &GameState, card_id: CardId) -> Option<PlayerId> {
    for si in 0..MAX_SITES {
        if gs.sites[si].is_faceup && gs.sites[si].cards.contains(&card_id) {
            return gs.sites[si].ruling_player;
        }
    }
    None
}

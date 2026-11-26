use crate::state::{DecisionPoint, GameState};
use crate::types::*;

/// Check if a player is currently meeting the Oathkeeper goal (§2.10).
/// Ties: current holder keeps the title.
pub fn recalculate_oathkeeper(gs: &mut GameState) {
    let n = gs.num_players as usize;
    match gs.oath_goal {
        OathGoal::Supremacy => {
            // Most sites ruled. Imperial players share Imperial sites, and Chancellor
            // holds the Oathkeeper of Supremacy for the Empire (§2.11).
            let mut scores = [0u8; MAX_PLAYERS];
            for p in 0..n {
                scores[p] = gs.count_sites_ruled(p as PlayerId);
            }
            let max_score = *scores[..n].iter().max().unwrap_or(&0);
            if max_score == 0 {
                return;
            }
            if let Some(holder) = gs.oathkeeper_holder {
                if scores[holder as usize] == max_score {
                    return; // holder keeps on tie
                }
            }
            // Prefer Chancellor if Imperial tied for max
            let chanc = gs.chancellor_index();
            if scores[chanc as usize] == max_score {
                transfer_oathkeeper(gs, chanc);
                return;
            }
            for p in 0..n {
                if scores[p] == max_score && gs.players[p].role == Role::Exile {
                    transfer_oathkeeper(gs, p as PlayerId);
                    return;
                }
            }
        }
        OathGoal::People => {
            if let Some(holder) = gs.peoples_favor_holder {
                if gs.oathkeeper_holder != Some(holder) {
                    transfer_oathkeeper(gs, holder);
                }
            }
        }
        OathGoal::Devotion => {
            if let Some(holder) = gs.darkest_secret_holder {
                if gs.oathkeeper_holder != Some(holder) {
                    transfer_oathkeeper(gs, holder);
                }
            }
        }
        OathGoal::Sanctuary => {
            let mut scores = [0u8; MAX_PLAYERS];
            for p in 0..n {
                scores[p] = gs.count_relics_and_banners(p as PlayerId);
            }
            let max_score = *scores[..n].iter().max().unwrap_or(&0);
            if max_score == 0 {
                return;
            }
            if let Some(holder) = gs.oathkeeper_holder {
                if scores[holder as usize] == max_score {
                    return;
                }
            }
            for p in 0..n {
                if scores[p] == max_score {
                    transfer_oathkeeper(gs, p as PlayerId);
                    return;
                }
            }
        }
    }
}

pub fn transfer_oathkeeper(gs: &mut GameState, new_holder: PlayerId) {
    if gs.oathkeeper_holder != Some(new_holder) {
        gs.oathkeeper_holder = Some(new_holder);
        gs.oathkeeper_side = TitleSide::Oathkeeper;
        // Chaos Cult (OATH-101): after another player takes Oathkeeper, take 1 favor from them
        for p in 0..gs.num_players {
            if p != new_holder
                && gs.player_has_card_access(p, 101)
                && gs.players[new_holder as usize].favor > 0
            {
                gs.players[new_holder as usize].favor -= 1;
                gs.players[p as usize].favor += 1;
            }
        }
    }
}

/// Check if a player meets their revealed Vision's win condition (§3.2).
pub fn meets_vision_goal(gs: &GameState, player: PlayerId) -> bool {
    let Some(vision) = gs.players[player as usize].revealed_vision else {
        return false;
    };
    if gs.visions_drawn < 3 {
        return false;
    }
    let n = gs.num_players as usize;
    match vision {
        CARD_VISION_CONQUEST => {
            let my = gs.count_sites_ruled(player);
            my > 0 && (0..n).all(|p| p == player as usize || gs.count_sites_ruled(p as PlayerId) < my)
        }
        CARD_VISION_REBELLION => gs.peoples_favor_holder == Some(player),
        CARD_VISION_FAITH => gs.darkest_secret_holder == Some(player),
        CARD_VISION_SANCTUARY => {
            let my = gs.count_relics_and_banners(player);
            my > 0
                && (0..n).all(|p| {
                    p == player as usize || gs.count_relics_and_banners(p as PlayerId) < my
                })
        }
        _ => false,
    }
}

/// Check Usurper Win (§3.1) and Visionary Win (§3.2) during Wake Phase.
pub fn check_start_of_turn_wins(gs: &mut GameState, player: PlayerId) -> bool {
    if gs.players[player as usize].role != Role::Exile {
        return false;
    }
    // §3.1 Usurper Win
    if gs.oathkeeper_holder == Some(player) && gs.oathkeeper_side == TitleSide::Usurper {
        declare_winner(gs, player, WinType::Usurper);
        return true;
    }
    // §3.2 Visionary Win
    if meets_vision_goal(gs, player) {
        declare_winner(gs, player, WinType::Vision);
        return true;
    }
    false
}

/// Find Citizen winning via Successor Goal if Empire wins (§3.3.1).
pub fn find_successor_winner(gs: &GameState) -> Option<PlayerId> {
    let chanc = gs.chancellor_index();
    let n = gs.num_players as usize;
    match gs.successor_goal {
        SuccessorGoal::MostRelicsBanners => {
            let chanc_score = gs.count_relics_and_banners(chanc);
            let mut best_citizen: Option<(PlayerId, u8)> = None;
            let mut tied = false;
            for p in 0..n {
                if gs.players[p].role == Role::Citizen {
                    let s = gs.count_relics_and_banners(p as PlayerId);
                    if s > chanc_score {
                        match best_citizen {
                            None => best_citizen = Some((p as PlayerId, s)),
                            Some((_, bs)) if s > bs => {
                                best_citizen = Some((p as PlayerId, s));
                                tied = false;
                            }
                            Some((_, bs)) if s == bs => tied = true,
                            _ => {}
                        }
                    }
                }
            }
            if tied {
                None
            } else {
                best_citizen.map(|(p, _)| p)
            }
        }
        SuccessorGoal::DarkestSecret => gs.darkest_secret_holder.filter(|&h| {
            gs.players[h as usize].role == Role::Citizen
        }),
        SuccessorGoal::PeoplesFavor => gs.peoples_favor_holder.filter(|&h| {
            gs.players[h as usize].role == Role::Citizen
        }),
        SuccessorGoal::GrandScepter => (0..n)
            .find(|&p| {
                gs.players[p].role == Role::Citizen && gs.players[p].has_relic(CARD_GRAND_SCEPTER)
            })
            .map(|p| p as PlayerId),
    }
}

/// Resolve Empire win (either Successor Citizen or Chancellor).
pub fn declare_empire_win(gs: &mut GameState) {
    if let Some(cit) = find_successor_winner(gs) {
        declare_winner(gs, cit, WinType::Successor);
    } else {
        let chanc = gs.chancellor_index();
        declare_winner(gs, chanc, WinType::OathkeeperDefault);
    }
}

/// Check End-of-Round Stable Regime die roll (§3.3).
/// Returns true if the game ended.
pub fn resolve_end_of_round_roll(gs: &mut GameState, roll: u8) -> bool {
    let empire_is_ok = gs
        .oathkeeper_holder
        .map(|h| gs.is_imperial(h))
        .unwrap_or(false);

    if gs.round_number < MAX_ROUNDS {
        if !empire_is_ok {
            return false;
        }
        let ends = match gs.round_number {
            5 => roll >= 6,
            6 => roll >= 5,
            7 => roll >= 3,
            _ => false,
        };
        if ends {
            declare_empire_win(gs);
            return true;
        }
        return false;
    }

    // Round 8: War Exhaustion (§3.4)
    // 1. Empire if Oathkeeper
    if empire_is_ok {
        declare_empire_win(gs);
        return true;
    }
    // 2. Usurper
    if let Some(h) = gs.oathkeeper_holder {
        if gs.players[h as usize].role == Role::Exile && gs.oathkeeper_side == TitleSide::Usurper {
            declare_winner(gs, h, WinType::Usurper);
            return true;
        }
    }
    // 3. Visionary (tiebreak: Conquest > Rebellion > Sanctuary > Faith)
    let priority = [
        CARD_VISION_CONQUEST,
        CARD_VISION_REBELLION,
        CARD_VISION_SANCTUARY,
        CARD_VISION_FAITH,
    ];
    for vis in priority {
        for p in 0..gs.num_players {
            if gs.players[p as usize].revealed_vision == Some(vis) && meets_vision_goal(gs, p) {
                declare_winner(gs, p, WinType::Vision);
                return true;
            }
        }
    }
    // 4. Empire default
    declare_empire_win(gs);
    true
}

pub fn declare_winner(gs: &mut GameState, winner: PlayerId, win_type: WinType) {
    gs.winner = Some(winner);
    gs.win_type = Some(win_type);
    if gs.chronicle_enabled {
        gs.phase = Phase::Chronicle;
        gs.decision = DecisionPoint::ChronicleVow { player: winner };
    } else {
        gs.is_game_over = true;
        gs.phase = Phase::GameOver;
        gs.decision = DecisionPoint::Terminal;
    }
}

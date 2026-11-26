use smallvec::SmallVec;

use crate::cards::{self, get_card};
use crate::engine::deals::{is_campaign_blocked_by_contract, on_campaign_declared_contracts};
use crate::engine::major_actions::{
    execute_travel, gain_warbands, kill_warbands_from_board, seize_darkest_secret,
    seize_peoples_favor,
};
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

// ── CAMPAIGN ELIGIBILITY (§5.5.1) ─────────────────────────────────────────

pub fn can_campaign_player(gs: &GameState, attacker: PlayerId, defender: PlayerId) -> bool {
    if attacker == defender || defender >= gs.num_players {
        return false;
    }
    // Vow of Peace (OATH-145): you cannot campaign
    if gs.player_has_card_access(attacker, 145) {
        return false;
    }
    let p = &gs.players[attacker as usize];
    if p.supply < 2 {
        return false;
    }
    if is_campaign_blocked_by_contract(gs, attacker, defender) {
        return false;
    }
    let site_idx = p.pawn_site;
    let defender_rules_site = gs.player_rules_site(defender, site_idx);
    let defender_pawn_here = gs.players[defender as usize].pawn_site == site_idx;
    if !defender_rules_site && !defender_pawn_here {
        return false;
    }
    // Must have at least one valid target
    defender_rules_site
        || defender_pawn_here
        || gs.count_sites_ruled(defender) > 0
}

pub fn can_campaign_bandits(gs: &GameState, attacker: PlayerId) -> bool {
    if gs.player_has_card_access(attacker, 145) {
        return false;
    }
    let p = &gs.players[attacker as usize];
    if p.supply < 2 {
        return false;
    }
    if p.has_relic(RELIC_BANDIT_CROWN) {
        return false; // Bandit Crown holder already rules empty sites
    }
    let site = &gs.sites[p.pawn_site as usize];
    site.is_faceup && site.ruling_player.is_none()
}

pub fn execute_campaign_declare(gs: &mut GameState, attacker: PlayerId, defender: Option<PlayerId>) {
    gs.players[attacker as usize].supply -= 2;
    gs.supply_spent_this_turn += 2;
    gs.actions_taken_this_turn += 1;

    if let Some(def) = defender {
        on_campaign_declared_contracts(gs, attacker, def);
    }

    let mut camp = CampaignState::new(attacker, defender);
    let site_idx = gs.players[attacker as usize].pawn_site;

    // If targeting Bandits, only target is current site -> jump straight to Battle Plans
    if defender.is_none() {
        camp.targets.push(CampaignTarget::Site(site_idx));
        camp.target_sites.push(site_idx);
        gs.campaign = Some(camp);
        begin_battle_plans(gs);
        return;
    }

    let def = defender.unwrap();
    // §5.5.2: if defender rules attacker's site, attacker MUST target it
    if gs.player_rules_site(def, site_idx) {
        camp.targets.push(CampaignTarget::Site(site_idx));
        camp.target_sites.push(site_idx);
    }

    // Determine Imperial allies (§5.5.3): if Imperial defends (and not Chancellor vs Citizen)
    let is_civil_war = gs.is_imperial(attacker) && gs.is_imperial(def);
    if !is_civil_war && gs.is_imperial(def) {
        for p in 0..gs.num_players {
            if p != attacker && p != def && gs.is_imperial(p) {
                camp.allies.push(p);
            }
        }
    }

    gs.campaign = Some(camp);
    gs.decision = DecisionPoint::CampaignTargets { player: attacker };
}

// ── TARGET SELECTION (§5.5.2) ─────────────────────────────────────────────

pub fn can_target_site(gs: &GameState, site_idx: SiteIndex) -> bool {
    let Some(ref camp) = gs.campaign else {
        return false;
    };
    let Some(def) = camp.defender else {
        return false;
    };
    if camp.target_sites.contains(&site_idx) {
        return false;
    }
    if !gs.player_rules_site(def, site_idx) {
        return false;
    }
    // Hidden Place (OATH-258) requires faceup secret to target
    if gs.sites[site_idx as usize].site_id == SITE_THE_HIDDEN_PLACE
        && gs.players[camp.attacker as usize].secrets_faceup == 0
    {
        return false;
    }
    true
}

pub fn execute_target_site(gs: &mut GameState, site_idx: SiteIndex) {
    if let Some(ref mut camp) = gs.campaign {
        if !camp.target_sites.contains(&site_idx) {
            camp.target_sites.push(site_idx);
            camp.targets.push(CampaignTarget::Site(site_idx));
        }
    }
}

pub fn can_target_relic(gs: &GameState, relic_slot: u8) -> bool {
    let Some(ref camp) = gs.campaign else {
        return false;
    };
    let Some(def) = camp.defender else {
        return false;
    };
    if gs.players[def as usize].pawn_site != gs.players[camp.attacker as usize].pawn_site {
        return false;
    }
    let Some(&rid) = gs.players[def as usize].relics.get(relic_slot as usize) else {
        return false;
    };
    // Circlet of Command (OATH-225): players cannot target your other relics
    if rid != RELIC_CIRCLET_OF_COMMAND && gs.players[def as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
        return false;
    }
    // Lost Tongue (OATH-157): cannot target defender's relics unless attacker rules a Nomad card
    if gs.player_has_card_access(def, 157) && !cards::denizens::player_rules_suit(gs, camp.attacker, Suit::Nomad) {
        return false;
    }
    !camp.targets.contains(&CampaignTarget::Relic(rid))
}

pub fn execute_target_relic(gs: &mut GameState, relic_slot: u8) {
    let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) else {
        return;
    };
    if let Some(&rid) = gs.players[def as usize].relics.get(relic_slot as usize) {
        if let Some(ref mut camp) = gs.campaign {
            camp.targets.push(CampaignTarget::Relic(rid));
        }
    }
}

pub fn can_target_banner(gs: &GameState, banner: Banner) -> bool {
    let Some(ref camp) = gs.campaign else {
        return false;
    };
    let Some(def) = camp.defender else {
        return false;
    };
    if gs.players[def as usize].pawn_site != gs.players[camp.attacker as usize].pawn_site {
        return false;
    }
    if gs.players[def as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
        return false;
    }
    // Lost Tongue (OATH-157)
    if gs.player_has_card_access(def, 157) && !cards::denizens::player_rules_suit(gs, camp.attacker, Suit::Nomad) {
        return false;
    }
    // Tome Guardians (OATH-110): enemies cannot target Darkest Secret
    if banner == Banner::DarkestSecret
        && crate::engine::major_actions::is_blocked_by_enemy_card(gs, camp.attacker, 110)
    {
        return false;
    }
    // Hall of Debate (OATH-201): players cannot target People's Favor
    if banner == Banner::PeoplesFavor
        && gs.sites.iter().any(|s| s.is_faceup && s.cards.contains(&EDIFICE_HALL_OF_DEBATE))
    {
        return false;
    }
    let held = match banner {
        Banner::PeoplesFavor => gs.peoples_favor_holder == Some(def),
        Banner::DarkestSecret => gs.darkest_secret_holder == Some(def),
    };
    held && !camp.targets.contains(&CampaignTarget::Banner(banner))
}

pub fn execute_target_banner(gs: &mut GameState, banner: Banner) {
    if let Some(ref mut camp) = gs.campaign {
        camp.targets.push(CampaignTarget::Banner(banner));
    }
}

pub fn can_target_pawn(gs: &GameState) -> bool {
    let Some(ref camp) = gs.campaign else {
        return false;
    };
    let Some(def) = camp.defender else {
        return false;
    };
    gs.players[def as usize].pawn_site == gs.players[camp.attacker as usize].pawn_site
        && !camp.targets.contains(&CampaignTarget::Pawn)
}

pub fn execute_target_pawn(gs: &mut GameState) {
    if let Some(ref mut camp) = gs.campaign {
        camp.targets.push(CampaignTarget::Pawn);
    }
}

pub fn execute_done_targets(gs: &mut GameState) {
    begin_battle_plans(gs);
}

// ── DICE COLLECTION & BATTLE PLANS (§5.5.2 - §5.5.3) ──────────────────────

fn begin_battle_plans(gs: &mut GameState) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;
    camp.attack_dice = gs.players[atk as usize].warbands_board as i8;
    // Vow of Union (OATH-185): warbands at sites you rule add to attacking force
    if gs.player_has_card_access(atk, 185) {
        for si in 0..MAX_SITES as u8 {
            if gs.player_rules_site(atk, si) {
                camp.attack_dice += gs.sites[si as usize].warbands as i8;
            }
        }
    }

    let mut def_dice: i8 = 0;
    let has_sprawling_rampart = camp.defender.map_or(false, |d| {
        gs.sites.iter().enumerate().any(|(si, s)| {
            s.is_faceup
                && s.cards.contains(&EDIFICE_SPRAWLING_RAMPART)
                && gs.player_rules_site(d, si as SiteIndex)
        })
    });
    let has_sealing_ward = camp.defender.map_or(false, |d| gs.player_has_card_access(d, 72));

    for &t in &camp.targets {
        match t {
            CampaignTarget::Site(si) => {
                let s = &gs.sites[si as usize];
                def_dice += get_card(s.site_id).defense as i8;
                if has_sprawling_rampart {
                    def_dice += 1;
                }
                // Mountain (OATH-249): -1 attack die; Plains (OATH-251): +1 attack die
                if s.site_id == SITE_MOUNTAIN {
                    camp.attack_dice -= 1;
                } else if s.site_id == SITE_PLAINS {
                    camp.attack_dice += 1;
                }
                // Bandit Rampart (OATH-200): -2 attack dice if this site is targeted
                if s.cards.contains(&EDIFICE_BANDIT_RAMPART) {
                    camp.attack_dice -= 2;
                }
            }
            CampaignTarget::Relic(rid) => {
                def_dice += get_card(rid).defense as i8;
                if has_sealing_ward {
                    def_dice += 1; // Sealing Ward (OATH-072)
                }
            }
            CampaignTarget::Banner(Banner::PeoplesFavor) => {
                def_dice += gs.peoples_favor_tokens as i8;
            }
            CampaignTarget::Banner(Banner::DarkestSecret) => {
                def_dice += gs.darkest_secret_tokens as i8;
            }
            CampaignTarget::Pawn => {
                def_dice += 1; // Player board shield
                if let Some(d) = camp.defender {
                    if gs.players[d as usize].has_relic(RELIC_CIRCLET_OF_COMMAND) {
                        def_dice += 1;
                    }
                }
            }
        }
    }

    // Oathkeeper (+1) / Usurper (+2) defense dice (§5.5.2)
    if let Some(d) = camp.defender {
        if gs.oathkeeper_holder == Some(d) {
            def_dice += match gs.oathkeeper_side {
                TitleSide::Oathkeeper => 1,
                TitleSide::Usurper => 2,
            };
        }
    }

    camp.defense_dice = def_dice;
    gs.campaign = Some(camp);

    // Check if attacker has any battle plans
    let atk_bps = list_usable_battle_plans(gs, atk, true);
    if !atk_bps.is_empty() {
        gs.decision = DecisionPoint::CampaignBattlePlan {
            player: atk,
            is_attacker: true,
        };
    } else {
        advance_to_defender_battle_plans(gs);
    }
}

pub fn list_usable_battle_plans(gs: &GameState, player: PlayerId, is_attacker: bool) -> SmallVec<[CardId; 10]> {
    let Some(ref camp) = gs.campaign else {
        return SmallVec::new();
    };
    // Marsh Spirit (OATH-192): players who target this site cannot use battle plans
    if is_attacker
        && camp
            .target_sites
            .iter()
            .any(|&si| gs.sites[si as usize].cards.contains(&192))
    {
        return SmallVec::new();
    }
    // Specialist (OATH-114): defender cannot use battle plans
    if !is_attacker && camp.active_bp_cards_attacker.contains(&114) {
        return SmallVec::new();
    }

    let enemy = if is_attacker { camp.defender } else { Some(camp.attacker) };
    let enemy_true_names = enemy.map_or(false, |e| gs.player_has_card_access(e, 41));
    let enemy_beast_tamer = enemy.map_or(false, |e| gs.player_has_card_access(e, 90));
    let extra_secret = if enemy.map_or(false, |e| gs.player_has_card_access(e, 66)) { 1 } else { 0 };
    let extra_favor = if enemy.map_or(false, |e| gs.player_has_card_access(e, 184)) { 1 } else { 0 };

    let mut out = SmallVec::new();
    let p = &gs.players[player as usize];

    let mut check_card = |cid: CardId| {
        if cid == CARD_EMPTY || camp.used_battle_plans.contains(&cid) || out.contains(&cid) {
            return;
        }
        let def = get_card(cid);
        if (def.tag_bits & TAG_BATTLE_PLAN) == 0 {
            return;
        }
        // True Names (OATH-041): cannot use battle plans matching enemy's advisers
        if enemy_true_names {
            if let (Some(e), Some(suit)) = (enemy, def.suit) {
                if gs.players[e as usize].has_faceup_adviser_suit(suit) {
                    return;
                }
            }
        }
        // Beast Tamer (OATH-090): cannot use Beast/Nomad battle plans
        if enemy_beast_tamer && matches!(def.suit, Some(Suit::Beast) | Some(Suit::Nomad)) {
            return;
        }
        let side_ok = match def.battle_plan_side {
            BattlePlanSide::Attacker => is_attacker,
            BattlePlanSide::Defender => !is_attacker,
            BattlePlanSide::Either => true,
            BattlePlanSide::None => false,
        };
        if !side_ok {
            return;
        }
        if p.favor < def.cost_favor + def.cost_burn_favor + extra_favor
            || p.secrets_faceup < def.cost_secrets + def.cost_burn_secrets + extra_secret
        {
            return;
        }
        if out.len() < 10 {
            out.push(cid);
        }
    };

    for &rid in &p.relics {
        check_card(rid);
    }
    for sl in 0..MAX_ADVISERS {
        if p.adviser_faceup[sl] {
            check_card(p.advisers[sl]);
        }
    }
    // Cards at pawn's site or sites ruled by player (excluding opponent's ruled sites §7.5.1)
    for si in 0..MAX_SITES as u8 {
        let s = &gs.sites[si as usize];
        if !s.is_faceup {
            continue;
        }
        let ruled_by_opp = if is_attacker {
            camp.defender.map_or(false, |d| gs.player_rules_site(d, si))
        } else {
            gs.player_rules_site(camp.attacker, si)
        };
        if !ruled_by_opp && (p.pawn_site == si || gs.player_rules_site(player, si)) {
            for sl in 0..s.capacity as usize {
                check_card(s.cards[sl]);
            }
        }
    }
    out
}

pub fn execute_use_battle_plan(gs: &mut GameState, player: PlayerId, is_attacker: bool, bp_slot: u8) {
    let bps = list_usable_battle_plans(gs, player, is_attacker);
    let Some(&cid) = bps.get(bp_slot as usize) else {
        return;
    };
    let def = get_card(cid);
    if def.cost_burn_favor > 0 {
        gs.players[player as usize].favor -= def.cost_burn_favor;
    }
    if def.cost_burn_secrets > 0 {
        gs.players[player as usize].secrets_faceup -= def.cost_burn_secrets;
        gs.shared_secrets += def.cost_burn_secrets;
    }
    if let Some(ref mut camp) = gs.campaign {
        camp.used_battle_plans.push(cid);
        if is_attacker {
            camp.active_bp_cards_attacker.push(cid);
        } else {
            camp.active_bp_cards_defender.push(cid);
        }
    }
    cards::denizens::apply_battle_plan(gs, player, is_attacker, cid);

    // Stay in battle plan decision if more remain, else advance
    let next_bps = list_usable_battle_plans(gs, player, is_attacker);
    if next_bps.is_empty() {
        execute_done_battle_plans(gs, is_attacker);
    }
}

pub fn execute_done_battle_plans(gs: &mut GameState, is_attacker: bool) {
    if is_attacker {
        if let Some(ref mut camp) = gs.campaign {
            camp.attacker_bp_done = true;
        }
        advance_to_defender_battle_plans(gs);
    } else {
        if let Some(ref mut camp) = gs.campaign {
            camp.defender_bp_done = true;
        }
        resolve_campaign_dice(gs);
    }
}

fn advance_to_defender_battle_plans(gs: &mut GameState) {
    let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) else {
        // Bandits: resolve immediately
        resolve_campaign_dice(gs);
        return;
    };
    // Give defender a 1-message ReactiveTalk window before defense battle plans!
    gs.effect_stack
        .push(PendingEffect::ResumeCampaignAfterReactiveTalk);
    gs.decision = DecisionPoint::ReactiveTalk {
        player: def,
        context: ReactiveContext::CampaignDefense,
    };
}

pub fn resume_campaign_after_reactive_talk(gs: &mut GameState) {
    let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) else {
        resolve_campaign_dice(gs);
        return;
    };
    let def_bps = list_usable_battle_plans(gs, def, false);
    if !def_bps.is_empty() {
        gs.decision = DecisionPoint::CampaignBattlePlan {
            player: def,
            is_attacker: false,
        };
    } else {
        resolve_campaign_dice(gs);
    }
}

// ── DICE ROLLS & SACRIFICE (§5.5.4 - §5.5.6) ──────────────────────────────

/// Roll official Oath defense dice (faces: 0, 0, 1, 1, 2, x2-multiplier) and attack dice
/// (faces: hollow, hollow, hollow, 1 sword, 1 sword + 1 skull, 2 swords + 2 skulls).
fn resolve_campaign_dice(gs: &mut GameState) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };

    // Peace Envoy (OATH-125): attacker pays favor = defense dice -> instant victory, no warbands killed
    if camp.active_bp_cards_attacker.contains(&125) {
        if let Some(def) = camp.defender {
            let pay = (camp.defense_dice.max(0) as u8).min(gs.players[camp.attacker as usize].favor);
            gs.players[camp.attacker as usize].favor -= pay;
            gs.players[def as usize].favor += pay;
        }
        camp.attacker_won = Some(true);
        gs.campaign = Some(camp);
        resolve_attacker_victory(gs);
        return;
    }

    // Hearts and Minds (OATH-138): defender wins immediately
    if camp.active_bp_cards_defender.contains(&138) {
        camp.attacker_won = Some(false);
        gs.campaign = Some(camp);
        resolve_attacker_defeat(gs);
        return;
    }

    // §5.5.3: If attack_dice < 0, add |attack_dice| to defense_dice
    if camp.attack_dice < 0 {
        camp.defense_dice += -camp.attack_dice;
        camp.attack_dice = 0;
    }
    let atk_dice = camp.attack_dice.clamp(0, 10) as u8;
    let def_dice = camp.defense_dice.clamp(0, 10) as u8;

    let ignore_single_shields = camp.active_bp_cards_attacker.contains(&14); // Rain Boots
    let atk_war_tortoise = camp.active_bp_cards_attacker.contains(&187);
    let def_war_tortoise = camp.active_bp_cards_defender.contains(&187);
    let ignore_hollow_swords = camp.active_bp_cards_defender.contains(&57)
        && camp.defender.map_or(false, |d| gs.darkest_secret_holder == Some(d)); // Rusting Ray
    let ignore_skulls = camp.active_bp_cards_attacker.contains(&104) // Outriders
        || camp.active_bp_cards_attacker.contains(&45)  // Rangers
        || camp.active_bp_cards_attacker.contains(&60)  // Kindred Warriors
        || camp.active_bp_cards_attacker.contains(&137); // The Great Levy

    // 1. Roll Defense (§5.5.4)
    let mut shields: i16 = 0;
    let mut doubles: u32 = 0;
    for _ in 0..def_dice {
        match gs.rng.gen_range_u8(6) {
            0 | 1 => {}
            2 | 3 => {
                if !ignore_single_shields {
                    shields += 1;
                }
            }
            4 => {
                if !atk_war_tortoise {
                    shields += 2;
                }
            }
            _ => doubles += 1,
        }
    }
    if doubles > 0 {
        shields = shields.saturating_mul(1i16.checked_shl(doubles.min(4)).unwrap_or(16));
    }

    // Add defending warbands
    for &si in &camp.target_sites {
        let s = &gs.sites[si as usize];
        if camp.defender.is_none() {
            shields += get_card(s.site_id).defense as i16;
        } else {
            shields += s.warbands as i16;
        }
    }
    if let Some(def) = camp.defender {
        let def_site = gs.players[def as usize].pawn_site;
        if def_site == gs.players[camp.attacker as usize].pawn_site
            || camp.target_sites.contains(&def_site)
        {
            shields += gs.players[def as usize].warbands_board as i16;
        }
        for &ally in &camp.allies {
            let asite = gs.players[ally as usize].pawn_site;
            if asite == gs.players[camp.attacker as usize].pawn_site
                || camp.target_sites.contains(&asite)
            {
                shields += gs.players[ally as usize].warbands_board as i16;
            }
        }
    }

    // 2. Roll Attack (§5.5.5)
    let mut full_swords: i16 = 0;
    let mut hollow_swords: i16 = 0;
    let mut skulls: u8 = 0;
    for _ in 0..atk_dice {
        match gs.rng.gen_range_u8(6) {
            0 | 1 | 2 => {
                if !ignore_hollow_swords {
                    hollow_swords += 1;
                }
            }
            3 => full_swords += 1,
            4 => {
                full_swords += 1;
                skulls += 1;
            }
            _ => {
                if !def_war_tortoise {
                    full_swords += 2;
                }
                skulls += 2;
            }
        }
    }
    if !ignore_skulls {
        let killed = kill_warbands_from_board(gs, camp.attacker, skulls);
        camp.attacker_warbands_killed += killed;
    }
    camp.attack_swords = full_swords + (hollow_swords / 2);
    camp.defense_shields = shields;

    let atk = camp.attacker;
    let avail_force = gs.players[atk as usize].warbands_board;
    let def_vow_of_peace = camp.defender.map_or(false, |d| gs.player_has_card_access(d, 145));

    // 3. Sacrifice check (§5.5.6) — blocked by defender's Vow of Peace (145); boosted x3 by Zealots (87)
    if !def_vow_of_peace && camp.attack_swords <= camp.defense_shields {
        let deficit = (camp.defense_shields - camp.attack_swords + 1) as u16;
        let per_sac = if camp.active_bp_cards_attacker.contains(&87) { 3u16 } else { 1u16 };
        let needed = (deficit + per_sac - 1) / per_sac;
        if needed <= avail_force as u16 && needed <= 10 {
            gs.campaign = Some(camp);
            gs.decision = DecisionPoint::CampaignSacrifice {
                player: atk,
                min_needed: needed as u8,
                max_available: avail_force,
            };
            return;
        }
    }

    let won = camp.attack_swords > camp.defense_shields;
    camp.attacker_won = Some(won);
    gs.campaign = Some(camp);
    if won {
        resolve_attacker_victory(gs);
    } else {
        resolve_attacker_defeat(gs);
    }
}

pub fn execute_campaign_sacrifice(gs: &mut GameState, sacrifice: u8) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;
    let actual = kill_warbands_from_board(gs, atk, sacrifice);
    camp.attacker_warbands_killed += actual;
    let mult = if camp.active_bp_cards_attacker.contains(&87) { 3 } else { 1 };
    camp.attack_swords += (actual as i16) * mult;
    let won = camp.attack_swords > camp.defense_shields;
    camp.attacker_won = Some(won);
    gs.campaign = Some(camp);

    if won {
        resolve_attacker_victory(gs);
    } else {
        resolve_attacker_defeat(gs);
    }
}

// ── VICTORY & DEFEAT RESOLUTION (§5.5.6 - §5.5.8) ─────────────────────────

fn resolve_attacker_defeat(gs: &mut GameState) {
    let Some(camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;
    // Traveling Doctor (51) / Billowing Fog (59): kill no warbands when defeated
    let no_loss = camp.active_bp_cards_attacker.contains(&51)
        || camp.active_bp_cards_attacker.contains(&59);
    if !no_loss {
        let kill_all = camp.active_bp_cards_attacker.contains(&108); // Shield Wall
        let amt = if kill_all {
            gs.players[atk as usize].warbands_board
        } else {
            gs.players[atk as usize].warbands_board / 2
        };
        kill_warbands_from_board(gs, atk, amt);
    }

    // Defender post-combat battle plans
    if let Some(def) = camp.defender {
        for &cid in &camp.active_bp_cards_defender {
            cards::denizens::apply_post_combat_victory(gs, def, false, cid);
        }
    }

    finish_campaign(gs);
}

fn resolve_attacker_victory(gs: &mut GameState) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;

    // 1. Defeated defender kills half (rounded down) of defending force (§5.5.6)
    let mut def_killed: u8 = 0;
    if let Some(def) = camp.defender {
        // Kill half at targeted sites, return remainder to defender's board (or Chancellor if Imperial)
        let sticky_fire = camp.active_bp_cards_attacker.contains(&RELIC_STICKY_FIRE);
        let obsidian_cage = camp.active_bp_cards_attacker.contains(&RELIC_OBSIDIAN_CAGE);

        for &si in &camp.target_sites {
            let wb = gs.sites[si as usize].warbands;
            if wb == 0 {
                continue;
            }
            let kill = if sticky_fire { wb } else { wb / 2 };
            let surv = wb - kill;
            def_killed += kill;
            gs.sites[si as usize].warbands = 0;
            gs.sites[si as usize].ruling_player = None;
            gs.sites[si as usize].warband_color = None;

            let owner_bank = if gs.is_imperial(def) {
                gs.chancellor_index()
            } else {
                def
            };
            gs.players[owner_bank as usize].warbands_bank += kill;
            if obsidian_cage {
                gs.obsidian_cage_warbands[owner_bank as usize] += surv;
            } else {
                gs.players[owner_bank as usize].warbands_board += surv;
            }
        }
        // Defender's board warbands if pawn was present
        let def_site = gs.players[def as usize].pawn_site;
        if def_site == gs.players[atk as usize].pawn_site || camp.target_sites.contains(&def_site) {
            let bwb = gs.players[def as usize].warbands_board;
            let kill = if sticky_fire { bwb } else { bwb / 2 };
            def_killed += kill_warbands_from_board(gs, def, kill);
        }
        if sticky_fire && gs.players[atk as usize].favor > 0 {
            gs.players[atk as usize].favor -= 1;
            gs.players[def as usize].favor += 1;
        }
    }
    camp.defender_warbands_killed = def_killed;

    // Cursed Cauldron (OATH-212): gain 1 warband per enemy warband killed
    if camp.active_bp_cards_attacker.contains(&RELIC_CURSED_CAULDRON) && def_killed > 0 {
        gain_warbands(gs, atk, def_killed);
    }

    // 2. Seize targeted Relics and Banners (§5.5.7.II)
    if let Some(def) = camp.defender {
        for &t in &camp.targets {
            match t {
                CampaignTarget::Relic(rid) => {
                    if let Some(pos) = gs.players[def as usize].relics.iter().position(|&r| r == rid) {
                        gs.players[def as usize].relics.remove(pos);
                        gs.players[atk as usize].relics.push(rid);
                        if rid == CARD_GRAND_SCEPTER {
                            gs.scepter_taken_this_turn = true;
                        }
                    }
                }
                CampaignTarget::Banner(Banner::PeoplesFavor) => seize_peoples_favor(gs, atk),
                CampaignTarget::Banner(Banner::DarkestSecret) => seize_darkest_secret(gs, atk),
                _ => {}
            }
        }
    }

    // 3. Attacker post-combat battle plans
    for &cid in &camp.active_bp_cards_attacker {
        cards::denizens::apply_post_combat_victory(gs, atk, true, cid);
    }

    // 4. Queue warband placement on targeted sites (§5.5.7.I)
    camp.remaining_sites_to_place = camp.target_sites.clone();
    gs.campaign = Some(camp);
    prompt_next_site_placement(gs);
}

fn prompt_next_site_placement(gs: &mut GameState) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;

    // Ring of Devotion (OATH-222): cannot place warbands at sites
    if gs.players[atk as usize].has_relic(RELIC_RING_OF_DEVOTION) {
        camp.remaining_sites_to_place.clear();
    }

    if let Some(si) = camp.remaining_sites_to_place.first().copied() {
        let max_wb = gs.players[atk as usize].warbands_board.min(10);
        if max_wb > 0 {
            gs.campaign = Some(camp);
            gs.decision = DecisionPoint::CampaignPlaceWarbands {
                player: atk,
                site: si,
                max_warbands: max_wb,
            };
            return;
        }
        camp.remaining_sites_to_place.remove(0);
        gs.campaign = Some(camp);
        prompt_next_site_placement(gs);
        return;
    }

    // Done placing warbands -> check Banish (§5.5.7.III)
    if camp.targets.contains(&CampaignTarget::Pawn) {
        if let Some(def) = camp.defender {
            let def_site = gs.players[def as usize].pawn_site;
            let mut allowed_sites = 0u8;
            for si in 0..MAX_SITES as u8 {
                if si != def_site && gs.sites[si as usize].is_faceup {
                    allowed_sites |= 1u8 << si;
                }
            }
            if allowed_sites != 0 {
                gs.effect_stack
                    .push(PendingEffect::ResumeCampaignBanish { defender: def });
                gs.decision = DecisionPoint::ChooseSite {
                    player: atk,
                    reason: ChoiceReason::BanishDestination,
                    allowed_mask: allowed_sites,
                };
                return;
            }
        }
    }

    finish_campaign(gs);
}

pub fn execute_place_warbands(gs: &mut GameState, count: u8) {
    let Some(mut camp) = gs.campaign.clone() else {
        return;
    };
    let atk = camp.attacker;
    if !camp.remaining_sites_to_place.is_empty() {
        let si = camp.remaining_sites_to_place.remove(0);
        let actual = count.min(gs.players[atk as usize].warbands_board);
        if actual > 0 {
            gs.players[atk as usize].warbands_board -= actual;
            gs.sites[si as usize].warbands = actual;
            gs.sites[si as usize].ruling_player = Some(atk);
            gs.sites[si as usize].warband_color =
                Some(if gs.is_imperial(atk) { 0 } else { atk });
        }
    }
    gs.campaign = Some(camp);
    prompt_next_site_placement(gs);
}

pub fn execute_banish_travel(gs: &mut GameState, defender: PlayerId, dest_site: SiteIndex) {
    execute_travel(gs, defender, dest_site, true);
    let atk = gs.campaign.as_ref().map(|c| c.attacker).unwrap_or(gs.current_player);
    if gs.players[defender as usize].favor > 0 {
        gs.decision = DecisionPoint::CampaignBanishBurn {
            player: atk,
            defender,
        };
    } else {
        finish_campaign(gs);
    }
}

pub fn execute_banish_burn(gs: &mut GameState, defender: PlayerId, burn: bool) {
    if burn {
        let half = gs.players[defender as usize].favor / 2;
        gs.players[defender as usize].favor -= half;
        for _ in 0..half {
            let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
            gs.favor_banks[min_i] += 1;
        }
    }
    finish_campaign(gs);
}

pub fn finish_campaign(gs: &mut GameState) {
    if let Some(ref camp) = gs.campaign {
        if camp.defender.is_some() {
            let atk = camp.attacker;
            // Herald (OATH-143): after another player campaigns against a player, gain 1 favor
            for p in 0..gs.num_players {
                if p != atk && gs.player_has_card_access(p, 143) {
                    if let Some((idx, &val)) = gs.favor_banks.iter().enumerate().max_by_key(|&(_, v)| v) {
                        if val > 0 {
                            gs.favor_banks[idx] -= 1;
                            gs.players[p as usize].favor += 1;
                        }
                    }
                }
            }
        }
    }
    gs.campaign = None;
    recalculate_oathkeeper(gs);
    gs.decision = DecisionPoint::TurnAct {
        player: gs.current_player,
    };
}

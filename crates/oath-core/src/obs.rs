use crate::actions::NUM_ACTIONS;
use crate::cards::get_card;
use crate::engine::legal_mask;
use crate::state::*;
use crate::types::*;

/// Fixed observation tensor sizes:
/// - `obs_flat`: 1024 float32 features (player-relative, imperfect-info exact)
/// - `card_ids`: 64 int32 card IDs for learned PyTorch `nn.Embedding(261, d)`
///   Layout of `card_ids`:
///     0..24   : 8 sites × 3 card slots (CARD_EMPTY or CARD_UNKNOWN if site facedown)
///     24..32  : 8 site IDs (CARD_UNKNOWN if facedown & not in observer's knowledge)
///     32..50  : 6 players (relative) × 3 adviser slots (CARD_UNKNOWN if opponent facedown & unknown)
///     50..56  : observer's held relics (up to 6)
///     56..62  : currently drawn search cards (up to 6, only visible to searcher unless reveal_all)
///     62..64  : observer's revealed vision + Reliquary peeked count sentinel
pub const OBS_FLAT_SIZE: usize = 1024;
pub const OBS_CARD_IDS_SIZE: usize = 64;

#[derive(Debug, Clone)]
pub struct Observation {
    pub obs_flat: [f32; OBS_FLAT_SIZE],
    pub card_ids: [i32; OBS_CARD_IDS_SIZE],
    pub action_mask: [i8; NUM_ACTIONS],
    pub acting_player: PlayerId,
}

pub fn encode_observation(gs: &GameState, observer: PlayerId) -> Observation {
    let mut flat = [0.0f32; OBS_FLAT_SIZE];
    let mut cids = [0i32; OBS_CARD_IDS_SIZE];
    let kb = &gs.knowledge[observer as usize];
    let n = gs.num_players as usize;
    let mut o = 0usize;

    // 1. Global state (40 floats)
    flat[o] = gs.round_number as f32 / MAX_ROUNDS as f32;
    flat[o + 1] = gs.visions_drawn as f32 / MAX_VISIONS_DRAWN as f32;
    flat[o + 2] = gs.num_players as f32 / MAX_PLAYERS as f32;
    flat[o + 3] = gs.shared_secrets as f32 / MAX_SECRETS_TOTAL as f32;
    flat[o + 4] = gs.world_deck.len() as f32 / 60.0;
    flat[o + 5] = gs.relic_deck.len() as f32 / 20.0;
    flat[o + 6] = gs.reliquary.len() as f32 / MAX_RELIQUARY as f32;
    flat[o + 7] = gs.peoples_favor_tokens as f32 / 10.0;
    flat[o + 8] = if gs.peoples_favor_is_mob { 1.0 } else { 0.0 };
    flat[o + 9] = gs.darkest_secret_tokens as f32 / 10.0;
    flat[o + 10] = if gs.oathkeeper_side == TitleSide::Usurper { 1.0 } else { 0.0 };
    flat[o + 11 + gs.oath_goal as usize] = 1.0; // 4
    flat[o + 15 + gs.successor_goal as usize] = 1.0; // 4
    for s in 0..NUM_SUITS {
        flat[o + 19 + s] = gs.favor_banks[s] as f32 / 12.0;
    }
    for r in 0..NUM_REGIONS {
        flat[o + 25 + r] = gs.discard_piles[r].len() as f32 / 20.0;
    }
    if let Some(h) = gs.oathkeeper_holder {
        flat[o + 28 + rel_idx(observer, h, gs.num_players)] = 1.0; // 6
    }
    if let Some(h) = gs.peoples_favor_holder {
        flat[o + 34 + rel_idx(observer, h, gs.num_players)] = 1.0; // 6
    }
    o += 40;

    // Darkest secret holder (6)
    if let Some(h) = gs.darkest_secret_holder {
        flat[o + rel_idx(observer, h, gs.num_players)] = 1.0;
    }
    o += 6;

    // 2. Map: 8 sites × 32 floats = 256 floats
    for si in 0..MAX_SITES {
        let s = &gs.sites[si];
        let base = o + si * 32;
        flat[base] = if s.is_faceup { 1.0 } else { 0.0 };
        flat[base + 1 + s.region as usize] = 1.0; // 3
        if s.is_faceup {
            let def = get_card(s.site_id);
            flat[base + 4] = s.capacity as f32 / 3.0;
            flat[base + 5] = def.defense as f32 / 4.0;
            flat[base + 6] = s.warbands as f32 / 10.0;
            flat[base + 7] = s.site_favor as f32 / 4.0;
            flat[base + 8] = s.site_secrets as f32 / 4.0;
            flat[base + 9] = s.relics.len() as f32 / 3.0;
            if let Some(r) = s.ruling_player {
                flat[base + 10 + rel_idx(observer, r, gs.num_players)] = 1.0; // 6
            }
            // 3 card slots summary: present, favor, secret, suit (3 × 5 = 15)
            for sl in 0..MAX_CARDS_PER_SITE {
                let c = s.cards[sl];
                cids[si * 3 + sl] = c as i32;
                let cb = base + 16 + sl * 5;
                if c != CARD_EMPTY {
                    flat[cb] = 1.0;
                    flat[cb + 1] = s.card_favor[sl] as f32 / 4.0;
                    flat[cb + 2] = s.card_secrets[sl] as f32 / 4.0;
                    if let Some(suit) = get_card(c).suit {
                        flat[cb + 3] = (suit as u8 + 1) as f32 / 6.0;
                    }
                    flat[cb + 4] = if get_card(c).edifice_is_ruined { 1.0 } else { 0.0 };
                }
            }
            cids[24 + si] = s.site_id as i32;
        } else {
            for sl in 0..MAX_CARDS_PER_SITE {
                cids[si * 3 + sl] = CARD_UNKNOWN as i32;
            }
            cids[24 + si] = if (kb.known_facedown_sites_mask & (1u8 << si)) != 0 {
                s.site_id as i32
            } else {
                CARD_UNKNOWN as i32
            };
        }
    }
    o += MAX_SITES * 32; // +256 = 302

    // 3. Players (player-relative: 6 × 48 = 288 floats)
    for rel in 0..MAX_PLAYERS {
        let base = o + rel * 48;
        if rel >= n {
            continue;
        }
        let pid = ((observer as usize + rel) % n) as PlayerId;
        let p = &gs.players[pid as usize];
        let is_self = pid == observer;
        flat[base] = 1.0; // player exists
        flat[base + 1 + p.role as usize] = 1.0; // 3
        flat[base + 4 + p.pawn_site as usize] = 1.0; // 8
        flat[base + 12] = p.supply as f32 / MAX_SUPPLY as f32;
        flat[base + 13] = p.favor as f32 / 15.0;
        flat[base + 14] = p.secrets_faceup as f32 / 10.0;
        flat[base + 15] = p.secrets_facedown as f32 / 10.0;
        flat[base + 16] = p.warbands_board as f32 / 14.0;
        flat[base + 17] = p.warbands_bank as f32 / 24.0;
        flat[base + 18] = p.relics.len() as f32 / 6.0;
        flat[base + 19] = if p.has_relic(CARD_GRAND_SCEPTER) { 1.0 } else { 0.0 };
        flat[base + 20] = if p.revealed_vision.is_some() { 1.0 } else { 0.0 };
        flat[base + 21] = gs.count_sites_ruled(pid) as f32 / MAX_SITES as f32;
        flat[base + 22] = p.talk_remaining as f32 / MAX_TALK_PER_TURN as f32;
        // 3 adviser slots (3 × 8 = 24 floats)
        for sl in 0..MAX_ADVISERS {
            let cid = p.advisers[sl];
            let visible = is_self || p.adviser_faceup[sl] || kb.knows_adviser(pid, sl);
            cids[32 + rel * 3 + sl] = if cid == CARD_EMPTY {
                CARD_EMPTY as i32
            } else if visible {
                cid as i32
            } else {
                CARD_UNKNOWN as i32
            };
            let ab = base + 24 + sl * 8;
            if cid != CARD_EMPTY {
                flat[ab] = 1.0;
                flat[ab + 1] = if p.adviser_faceup[sl] { 1.0 } else { 0.0 };
                if visible {
                    if let Some(suit) = get_card(cid).suit {
                        flat[ab + 2 + suit as usize] = 1.0; // 6
                    }
                }
            }
        }
    }
    o += MAX_PLAYERS * 48; // +288 = 590

    // Observer's relics & search cards in card_ids
    let obs_p = &gs.players[observer as usize];
    for (i, &rid) in obs_p.relics.iter().take(6).enumerate() {
        cids[50 + i] = rid as i32;
    }
    if let Some(ref s) = gs.search {
        if s.player == observer || s.reveal_all {
            for (i, &cid) in s.drawn_cards.iter().take(6).enumerate() {
                if s.remaining[i] {
                    cids[56 + i] = cid as i32;
                }
            }
        }
    }
    cids[62] = obs_p.revealed_vision.unwrap_or(CARD_EMPTY) as i32;
    cids[63] = kb.known_reliquary_mask as i32;

    // 4. DecisionPoint context (32 floats)
    let dp_idx = match gs.decision {
        DecisionPoint::TurnAct { .. } => 0,
        DecisionPoint::SearchResolve { .. } => 1,
        DecisionPoint::ChooseSite { .. } => 2,
        DecisionPoint::ChooseSiteCard { .. } => 3,
        DecisionPoint::ChooseAdviser { .. } => 4,
        DecisionPoint::ChooseSuit { .. } => 5,
        DecisionPoint::ChoosePlayer { .. } => 6,
        DecisionPoint::ChooseAmount { .. } => 7,
        DecisionPoint::ChooseYesNo { .. } => 8,
        DecisionPoint::CampaignTargets { .. } => 9,
        DecisionPoint::CampaignBattlePlan { .. } => 10,
        DecisionPoint::CampaignSacrifice { .. } => 11,
        DecisionPoint::CampaignPlaceWarbands { .. } => 12,
        DecisionPoint::CampaignBanishBurn { .. } => 13,
        DecisionPoint::DealCompose { .. } => 14,
        DecisionPoint::DealRespond { .. } => 15,
        DecisionPoint::ReactiveTalk { .. } => 16,
        DecisionPoint::ChronicleVow { .. } => 17,
        DecisionPoint::ChronicleEdifice { .. } => 18,
        DecisionPoint::Terminal => 19,
    };
    flat[o + dp_idx] = 1.0;
    if let Some(ref camp) = gs.campaign {
        flat[o + 20] = camp.attack_dice as f32 / 10.0;
        flat[o + 21] = camp.defense_dice as f32 / 10.0;
        flat[o + 22] = camp.attack_swords as f32 / 10.0;
        flat[o + 23] = camp.defense_shields as f32 / 10.0;
        flat[o + 24] = camp.targets.len() as f32 / 6.0;
    }
    if let Some(ref deal) = gs.deal {
        flat[o + 25] = deal.offer.favor as f32 / 10.0;
        flat[o + 26] = deal.offer.secrets as f32 / 10.0;
        flat[o + 27] = deal.request.favor as f32 / 10.0;
        flat[o + 28] = deal.request.secrets as f32 / 10.0;
        flat[o + 29] = deal.round as f32 / MAX_DEAL_ROUNDS as f32;
        flat[o + 30] = deal.contracts.len() as f32 / 2.0;
        flat[o + 31] = if deal.kind == DealKind::Citizenship { 1.0 } else { 0.0 };
    }
    o += 32; // = 622

    // 5. Active Tribunal contracts summary (6 × 8 = 48 floats)
    for (i, c) in gs.active_contracts.iter().take(6).enumerate() {
        let cb = o + i * 8;
        flat[cb] = 1.0;
        flat[cb + 1] = rel_idx(observer, c.party_a, gs.num_players) as f32 / 6.0;
        flat[cb + 2] = rel_idx(observer, c.party_b, gs.num_players) as f32 / 6.0;
        flat[cb + 3] = match c.clause {
            ContractClause::NonAggression { .. } => 0.25,
            ContractClause::SiteHandsOff { .. } => 0.5,
            ContractClause::MustCampaign { .. } => 0.75,
            ContractClause::MustNotRecoverBanner { .. } => 1.0,
        };
        flat[cb + 4] = match c.enforcement {
            EnforcementMode::HardEnforced => 1.0,
            EnforcementMode::PenaltyOnBreach { .. } => 0.5,
        };
    }
    o += 48; // = 670

    // 6. Recent Table Talk log (last 16 events × 16 floats = 256 floats)
    for (i, ev) in gs.talk_log.iter().rev().take(16).enumerate() {
        let tb = o + i * 16;
        flat[tb] = ev.round as f32 / MAX_ROUNDS as f32;
        flat[tb + 1] = (rel_idx(observer, ev.sender, gs.num_players) + 1) as f32 / 6.0;
        if let Some(tgt) = ev.target {
            flat[tb + 2] = (rel_idx(observer, tgt, gs.num_players) + 1) as f32 / 6.0;
        }
        flat[tb + 3 + (ev.intent as usize).min(9)] = 1.0;
        if let Some(suit) = ev.suit {
            flat[tb + 13] = (suit as u8 + 1) as f32 / 6.0;
        }
        if ev.shown_card.is_some() {
            flat[tb + 14] = 1.0; // verified truth!
        }
    }
    // Remaining floats up to 1024 stay 0.0 (reserved for future extensions)

    Observation {
        obs_flat: flat,
        card_ids: cids,
        action_mask: legal_mask(gs),
        acting_player: gs.decision.acting_player().unwrap_or(observer),
    }
}

#[inline]
fn rel_idx(observer: PlayerId, target: PlayerId, num_players: u8) -> usize {
    let n = num_players as usize;
    (target as usize + n - observer as usize) % n
}

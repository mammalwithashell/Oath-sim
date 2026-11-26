use crate::actions::{encode_action, resolve_rel_player, Action, NUM_ACTIONS};
use crate::engine::legal_mask;
use crate::rng::FastRng;
use crate::state::{DealKind, DecisionPoint, GameState};
use crate::types::*;

/// Uniform random legal action agent.
pub fn random_agent_action(gs: &GameState, rng: &mut FastRng) -> ActionId {
    let mask = legal_mask(gs);
    let mut legal = [0u16; NUM_ACTIONS];
    let mut count = 0usize;
    for (i, &m) in mask.iter().enumerate() {
        if m != 0 {
            legal[count] = i as ActionId;
            count += 1;
        }
    }
    if count == 0 {
        return encode_action(Action::EndActPhase);
    }
    legal[rng.gen_range_usize(count)]
}

/// Role-aware deterministic bot (Chancellor bot for Chancellor, Exile/Citizen bot for others).
pub fn heuristic_agent_action(gs: &GameState, rng: &mut FastRng) -> ActionId {
    let acting = gs.decision.acting_player().unwrap_or(gs.current_player);
    match gs.players[acting as usize].role {
        Role::Chancellor => chancellor_bot_action(gs, acting, rng),
        Role::Exile | Role::Citizen => exile_bot_action(gs, acting, rng),
    }
}

/// Shared sub-decision handler for deterministic bots (deals, campaigns, search, chronicle vow).
fn handle_sub_decision(gs: &GameState, acting: PlayerId, mask: &[i8; NUM_ACTIONS], rng: &mut FastRng) -> Option<ActionId> {
    let legal = |a: Action| mask[encode_action(a) as usize] != 0;

    match gs.decision {
        DecisionPoint::ReactiveTalk { .. } => {
            if legal(Action::PassTalk) {
                return Some(encode_action(Action::PassTalk));
            }
        }
        DecisionPoint::DealCompose { .. } => {
            if legal(Action::Confirm) {
                return Some(encode_action(Action::Confirm));
            }
        }
        DecisionPoint::DealRespond { .. } => {
            if let Some(ref deal) = gs.deal {
                // Rational deal evaluation: accept Citizenship if behind on sites/banners, or favorable resource trade
                let favorable = if deal.kind == DealKind::Citizenship {
                    gs.oathkeeper_holder != Some(acting) && gs.players[acting as usize].revealed_vision.is_none()
                } else {
                    deal.offer.favor + deal.offer.secrets * 2
                        >= deal.request.favor + deal.request.secrets * 2
                };
                if favorable && legal(Action::Confirm) {
                    return Some(encode_action(Action::Confirm));
                }
            }
            if legal(Action::Decline) {
                return Some(encode_action(Action::Decline));
            }
        }
        DecisionPoint::CampaignTargets { .. } => {
            // Pick oath-relevant target first, then confirm
            if gs.campaign.as_ref().map_or(false, |c| !c.targets.is_empty()) && legal(Action::Confirm) {
                return Some(encode_action(Action::Confirm));
            }
            if gs.oath_goal == OathGoal::People && legal(Action::CampaignTargetPeoplesFavor) {
                return Some(encode_action(Action::CampaignTargetPeoplesFavor));
            }
            if gs.oath_goal == OathGoal::Devotion && legal(Action::CampaignTargetDarkestSecret) {
                return Some(encode_action(Action::CampaignTargetDarkestSecret));
            }
            for si in 0..8u8 {
                if legal(Action::SelectSite(si)) {
                    return Some(encode_action(Action::SelectSite(si)));
                }
            }
            if legal(Action::CampaignTargetPeoplesFavor) {
                return Some(encode_action(Action::CampaignTargetPeoplesFavor));
            }
            if legal(Action::CampaignTargetDarkestSecret) {
                return Some(encode_action(Action::CampaignTargetDarkestSecret));
            }
            for sl in 0..6u8 {
                if legal(Action::CampaignTargetRelic(sl)) {
                    return Some(encode_action(Action::CampaignTargetRelic(sl)));
                }
            }
            if legal(Action::CampaignTargetPawn) {
                return Some(encode_action(Action::CampaignTargetPawn));
            }
        }
        DecisionPoint::CampaignBattlePlan { .. } => {
            // Use first available battle plan, else finish
            if legal(Action::CampaignUseBattlePlan(0)) {
                return Some(encode_action(Action::CampaignUseBattlePlan(0)));
            }
            if legal(Action::Decline) {
                return Some(encode_action(Action::Decline));
            }
        }
        DecisionPoint::CampaignSacrifice { min_needed, max_available, .. } => {
            if min_needed <= max_available && min_needed <= 3 && legal(Action::SelectAmount(min_needed)) {
                return Some(encode_action(Action::SelectAmount(min_needed)));
            }
            if legal(Action::SelectAmount(0)) {
                return Some(encode_action(Action::SelectAmount(0)));
            }
        }
        DecisionPoint::CampaignPlaceWarbands { max_warbands, .. } => {
            let place = (max_warbands / 2).max(1).min(max_warbands).min(10);
            if legal(Action::SelectAmount(place)) {
                return Some(encode_action(Action::SelectAmount(place)));
            }
        }
        DecisionPoint::SearchResolve { .. } => {
            // Exiles strongly prefer playing Revealed Vision (dest=3); everyone else prefers site > faceup adviser > facedown
            for dest in [3u8, 0, 1, 2] {
                for ci in 0..6u8 {
                    if legal(Action::SearchPlay { card_idx: ci, dest }) {
                        return Some(encode_action(Action::SearchPlay { card_idx: ci, dest }));
                    }
                }
            }
        }
        DecisionPoint::ChronicleVow { .. } => {
            // Pick a legal Oath Goal matching strengths
            let pref = [OathGoal::Supremacy, OathGoal::People, OathGoal::Sanctuary, OathGoal::Devotion];
            for g in pref {
                if legal(Action::VowOath(g)) {
                    return Some(encode_action(Action::VowOath(g)));
                }
            }
        }
        DecisionPoint::TurnAct { .. } => return None,
        _ => return Some(random_agent_action(gs, rng)),
    }
    None
}

/// Role-aware Chancellor Bot: defends the Empire & active Oathkeeper goal.
pub fn chancellor_bot_action(gs: &GameState, player: PlayerId, rng: &mut FastRng) -> ActionId {
    let mask = legal_mask(gs);
    if let Some(a) = handle_sub_decision(gs, player, &mask, rng) {
        return a;
    }
    let legal = |a: Action| mask[encode_action(a) as usize] != 0;
    let p = &gs.players[player as usize];

    // 1. Reclaim/hold Oath-critical banners or relics
    if gs.oath_goal == OathGoal::People && legal(Action::RecoverPeoplesFavor) {
        return encode_action(Action::RecoverPeoplesFavor);
    }
    if gs.oath_goal == OathGoal::Devotion && legal(Action::RecoverDarkestSecret) {
        return encode_action(Action::RecoverDarkestSecret);
    }
    if gs.oath_goal == OathGoal::Sanctuary {
        for sl in 0..3u8 {
            if legal(Action::RecoverRelic(sl)) {
                return encode_action(Action::RecoverRelic(sl));
            }
        }
    }

    // 2. Flip facedown advisers for economy
    for sl in 0..3u8 {
        if legal(Action::FlipAdviser(sl)) {
            return encode_action(Action::FlipAdviser(sl));
        }
    }

    // 3. If an Exile holds Oathkeeper/Usurper, prioritize campaigning against them!
    if let Some(ok) = gs.oathkeeper_holder {
        if ok != player && gs.players[ok as usize].role == Role::Exile && p.warbands_board >= 3 {
            for rel in 1..gs.num_players {
                if resolve_rel_player(player, rel, gs.num_players) == ok
                    && legal(Action::CampaignDeclare(rel))
                {
                    return encode_action(Action::CampaignDeclare(rel));
                }
            }
            // Travel toward the usurper's site
            let target_site = gs.players[ok as usize].pawn_site;
            if legal(Action::Travel(target_site)) {
                return encode_action(Action::Travel(target_site));
            }
        }
    }

    // 4. Offer Citizenship strategically if an Exile is strong and we have Reliquary relics
    if gs.round_number >= 3 && gs.actions_taken_this_turn == 0 {
        for rel in 1..gs.num_players {
            let tgt = resolve_rel_player(player, rel, gs.num_players);
            if gs.players[tgt as usize].role == Role::Exile
                && (gs.oathkeeper_holder == Some(tgt) || gs.count_sites_ruled(tgt) >= 2)
                && legal(Action::OfferCitizenship(rel))
            {
                return encode_action(Action::OfferCitizenship(rel));
            }
        }
    }

    // 5. Muster up to 6 warbands on board
    if p.warbands_board < 6 {
        for sl in 0..3u8 {
            if legal(Action::Muster(sl)) {
                return encode_action(Action::Muster(sl));
            }
        }
    }

    // 6. Trade for favor/secrets
    for sl in 0..3u8 {
        if legal(Action::TradeFavor(sl)) {
            return encode_action(Action::TradeFavor(sl));
        }
        if p.secrets_faceup < 2 && legal(Action::TradeSecrets(sl)) {
            return encode_action(Action::TradeSecrets(sl));
        }
    }

    // 7. Expand Imperial rule against Bandits if Supremacy
    if gs.oath_goal == OathGoal::Supremacy && p.warbands_board >= 4 && legal(Action::CampaignDeclareBandits) {
        return encode_action(Action::CampaignDeclareBandits);
    }

    // 8. Search if early in turn
    if gs.actions_taken_this_turn < 2 && legal(Action::SearchDeck) {
        return encode_action(Action::SearchDeck);
    }

    // 9. Travel to an unruled or high-value site
    if gs.actions_taken_this_turn < 2 {
        for si in 0..8u8 {
            if legal(Action::Travel(si)) && !gs.player_rules_site(player, si) {
                return encode_action(Action::Travel(si));
            }
        }
    }

    if legal(Action::EndActPhase) {
        return encode_action(Action::EndActPhase);
    }
    random_agent_action(gs, rng)
}

/// Role-aware Exile / Citizen Bot: pursues Usurper, Visionary, or Successor victory.
pub fn exile_bot_action(gs: &GameState, player: PlayerId, rng: &mut FastRng) -> ActionId {
    let mask = legal_mask(gs);
    if let Some(a) = handle_sub_decision(gs, player, &mask, rng) {
        return a;
    }
    let legal = |a: Action| mask[encode_action(a) as usize] != 0;
    let p = &gs.players[player as usize];

    // 1. Recover banners / relics aligned with Oath, Vision, or Successor goal
    let wants_pf = gs.oath_goal == OathGoal::People
        || p.revealed_vision == Some(CARD_VISION_REBELLION)
        || (p.role == Role::Citizen && gs.successor_goal == SuccessorGoal::PeoplesFavor);
    let wants_ds = gs.oath_goal == OathGoal::Devotion
        || p.revealed_vision == Some(CARD_VISION_FAITH)
        || (p.role == Role::Citizen && gs.successor_goal == SuccessorGoal::DarkestSecret);

    if wants_pf && legal(Action::RecoverPeoplesFavor) {
        return encode_action(Action::RecoverPeoplesFavor);
    }
    if wants_ds && legal(Action::RecoverDarkestSecret) {
        return encode_action(Action::RecoverDarkestSecret);
    }
    for sl in 0..3u8 {
        if legal(Action::RecoverRelic(sl)) {
            return encode_action(Action::RecoverRelic(sl));
        }
    }

    // 2. Flip advisers
    for sl in 0..3u8 {
        if legal(Action::FlipAdviser(sl)) {
            return encode_action(Action::FlipAdviser(sl));
        }
    }

    // 3. Build striking force
    if p.warbands_board < 5 {
        for sl in 0..3u8 {
            if legal(Action::Muster(sl)) {
                return encode_action(Action::Muster(sl));
            }
        }
    }

    // 4. Trade for favor/secrets to fuel banners & relics
    for sl in 0..3u8 {
        if p.favor < 4 && legal(Action::TradeFavor(sl)) {
            return encode_action(Action::TradeFavor(sl));
        }
        if p.secrets_faceup < 3 && legal(Action::TradeSecrets(sl)) {
            return encode_action(Action::TradeSecrets(sl));
        }
    }

    // 5. Campaign aggressively against Oathkeeper or Bandits when strong
    if p.warbands_board >= 4 {
        if let Some(ok) = gs.oathkeeper_holder {
            if ok != player {
                for rel in 1..gs.num_players {
                    if resolve_rel_player(player, rel, gs.num_players) == ok
                        && legal(Action::CampaignDeclare(rel))
                    {
                        return encode_action(Action::CampaignDeclare(rel));
                    }
                }
            }
        }
        if legal(Action::CampaignDeclareBandits) {
            return encode_action(Action::CampaignDeclareBandits);
        }
    }

    // 6. Search World Deck (to find Visions & denizens)
    if gs.actions_taken_this_turn < 2 && legal(Action::SearchDeck) {
        return encode_action(Action::SearchDeck);
    }

    // 7. Travel to explore facedown sites or sites with relics/cards
    if gs.actions_taken_this_turn < 2 {
        for si in 0..8u8 {
            if legal(Action::Travel(si))
                && (!gs.sites[si as usize].is_faceup || !gs.sites[si as usize].relics.is_empty())
            {
                return encode_action(Action::Travel(si));
            }
        }
        for si in 0..8u8 {
            if legal(Action::Travel(si)) && rng.gen_range_u8(3) == 0 {
                return encode_action(Action::Travel(si));
            }
        }
    }

    if legal(Action::EndActPhase) {
        return encode_action(Action::EndActPhase);
    }
    random_agent_action(gs, rng)
}

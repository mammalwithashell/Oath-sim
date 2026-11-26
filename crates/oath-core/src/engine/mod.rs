pub mod campaign;
pub mod chronicle;
pub mod deals;
pub mod major_actions;
pub mod minor_actions;
pub mod setup;
pub mod turn;
pub mod win;

use crate::actions::{decode_action, encode_action, resolve_rel_player, Action, NUM_ACTIONS};
use crate::cards;
use crate::state::*;
use crate::types::*;

/// Compute the exact binary legal action mask for the currently acting player.
pub fn legal_mask(gs: &GameState) -> [i8; NUM_ACTIONS] {
    let mut mask = [0i8; NUM_ACTIONS];
    if gs.is_game_over {
        return mask;
    }

    match gs.decision.clone() {
        DecisionPoint::TurnAct { player } => {
            // Travel (0..8)
            for si in 0..MAX_SITES as u8 {
                if major_actions::can_travel(gs, player, si) {
                    mask[encode_action(Action::Travel(si)) as usize] = 1;
                }
            }
            // Search (8..10)
            if major_actions::can_search_deck(gs, player) {
                mask[encode_action(Action::SearchDeck) as usize] = 1;
            }
            if major_actions::can_search_discard(gs, player) {
                mask[encode_action(Action::SearchDiscard) as usize] = 1;
            }
            // Muster / Trade (10..19)
            for sl in 0..MAX_CARDS_PER_SITE as u8 {
                if major_actions::can_muster(gs, player, sl) {
                    mask[encode_action(Action::Muster(sl)) as usize] = 1;
                }
                if major_actions::can_trade_favor(gs, player, sl) {
                    mask[encode_action(Action::TradeFavor(sl)) as usize] = 1;
                }
                if major_actions::can_trade_secrets(gs, player, sl) {
                    mask[encode_action(Action::TradeSecrets(sl)) as usize] = 1;
                }
            }
            // Recover (19..24)
            for sl in 0..3u8 {
                if major_actions::can_recover_relic(gs, player, sl) {
                    mask[encode_action(Action::RecoverRelic(sl)) as usize] = 1;
                }
            }
            if major_actions::can_recover_peoples_favor(gs, player) {
                mask[encode_action(Action::RecoverPeoplesFavor) as usize] = 1;
            }
            if major_actions::can_recover_darkest_secret(gs, player) {
                mask[encode_action(Action::RecoverDarkestSecret) as usize] = 1;
            }
            // Campaign Declare (24..30)
            for rel in 1..gs.num_players {
                let target = resolve_rel_player(player, rel, gs.num_players);
                if campaign::can_campaign_player(gs, player, target) {
                    mask[encode_action(Action::CampaignDeclare(rel)) as usize] = 1;
                }
            }
            if campaign::can_campaign_bandits(gs, player) {
                mask[encode_action(Action::CampaignDeclareBandits) as usize] = 1;
            }
            // Minor Actions
            for sl in 0..MAX_ADVISERS as u8 {
                if minor_actions::can_flip_adviser(gs, player, sl) {
                    mask[encode_action(Action::FlipAdviser(sl)) as usize] = 1;
                }
                if minor_actions::can_discard_adviser(gs, player, sl) {
                    mask[encode_action(Action::DiscardAdviser(sl)) as usize] = 1;
                }
            }
            for sl in 0..11u8 {
                if minor_actions::can_use_card_action(gs, player, sl) {
                    mask[encode_action(Action::UseCardAction(sl)) as usize] = 1;
                }
            }
            for sl in 0..3u8 {
                if minor_actions::can_peek_site_relic(gs, player, sl) {
                    mask[encode_action(Action::PeekSiteRelic(sl)) as usize] = 1;
                }
            }
            if minor_actions::can_peek_reliquary(gs, player) {
                mask[encode_action(Action::PeekReliquary) as usize] = 1;
            }
            if gs.actions_taken_this_turn < 24 && minor_actions::can_move_warbands_to_board(gs, player) {
                mask[encode_action(Action::MoveWarbandsToBoard) as usize] = 1;
            }
            if gs.actions_taken_this_turn < 24 && minor_actions::can_move_warbands_to_site(gs, player) {
                mask[encode_action(Action::MoveWarbandsToSite) as usize] = 1;
            }
            for rel in 1..gs.num_players {
                let target = resolve_rel_player(player, rel, gs.num_players);
                if gs.actions_taken_this_turn < 24 && minor_actions::can_offer_citizenship(gs, player, target) {
                    mask[encode_action(Action::OfferCitizenship(rel)) as usize] = 1;
                }
                if minor_actions::can_exile_citizen(gs, player, target) {
                    mask[encode_action(Action::ExileCitizen(rel)) as usize] = 1;
                }
            }
            if minor_actions::can_self_exile(gs, player) {
                mask[encode_action(Action::SelfExile) as usize] = 1;
            }
            // Table Talk (budgeted per turn)
            if gs.players[player as usize].talk_remaining > 0 {
                enable_talk_actions(gs, player, &mut mask);
            }
            // Always allow ending Act phase
            mask[encode_action(Action::EndActPhase) as usize] = 1;
        }

        DecisionPoint::SearchResolve { player } => {
            if let Some(ref s) = gs.search {
                let mut any = false;
                for (i, &cid) in s.drawn_cards.iter().enumerate() {
                    if !s.remaining[i] {
                        continue;
                    }
                    for dest in 0..4u8 {
                        if major_actions::can_play_search_card(gs, player, cid, dest) {
                            mask[encode_action(Action::SearchPlay {
                                card_idx: i as u8,
                                dest,
                            }) as usize] = 1;
                        }
                    }
                    mask[encode_action(Action::SearchDiscardCard(i as u8)) as usize] = 1;
                    any = true;
                }
                if !any {
                    mask[encode_action(Action::Confirm) as usize] = 1;
                }
            } else {
                mask[encode_action(Action::Confirm) as usize] = 1;
            }
        }

        DecisionPoint::ChooseSite { allowed_mask, .. } => {
            let mut any = false;
            for si in 0..MAX_SITES as u8 {
                if (allowed_mask & (1u8 << si)) != 0 {
                    mask[encode_action(Action::SelectSite(si)) as usize] = 1;
                    any = true;
                }
            }
            if !any {
                mask[encode_action(Action::Decline) as usize] = 1;
            }
        }

        DecisionPoint::ChooseSiteCard { allowed_slots, .. }
        | DecisionPoint::ChooseAdviser { allowed_slots, .. } => {
            let mut any = false;
            for sl in 0..4u8 {
                if (allowed_slots & (1u8 << sl)) != 0 {
                    mask[encode_action(Action::SelectSlot(sl)) as usize] = 1;
                    any = true;
                }
            }
            if !any {
                mask[encode_action(Action::Decline) as usize] = 1;
            }
        }

        DecisionPoint::ChooseSuit { allowed_mask, .. } => {
            let mut any = false;
            for s in Suit::ALL {
                if (allowed_mask & s.bit()) != 0 {
                    mask[encode_action(Action::SelectSuit(s)) as usize] = 1;
                    any = true;
                }
            }
            if !any {
                mask[encode_action(Action::SelectSuit(Suit::Order)) as usize] = 1;
            }
        }

        DecisionPoint::ChoosePlayer {
            player,
            allowed_mask,
            ..
        } => {
            let mut any = false;
            for rel in 0..gs.num_players {
                let target = resolve_rel_player(player, rel, gs.num_players);
                if (allowed_mask & (1u8 << target)) != 0 {
                    mask[encode_action(Action::SelectRelPlayer(rel)) as usize] = 1;
                    any = true;
                }
            }
            if !any {
                mask[encode_action(Action::Decline) as usize] = 1;
            }
        }

        DecisionPoint::ChooseAmount { min, max, .. } => {
            let hi = max.min(10);
            let lo = min.min(hi);
            for a in lo..=hi {
                mask[encode_action(Action::SelectAmount(a)) as usize] = 1;
            }
        }

        DecisionPoint::ChooseYesNo { .. } | DecisionPoint::CampaignBanishBurn { .. } => {
            mask[encode_action(Action::Confirm) as usize] = 1;
            mask[encode_action(Action::Decline) as usize] = 1;
        }

        DecisionPoint::CampaignTargets { .. } => {
            for si in 0..MAX_SITES as u8 {
                if campaign::can_target_site(gs, si) {
                    mask[encode_action(Action::SelectSite(si)) as usize] = 1;
                }
            }
            for sl in 0..6u8 {
                if campaign::can_target_relic(gs, sl) {
                    mask[encode_action(Action::CampaignTargetRelic(sl)) as usize] = 1;
                }
            }
            if campaign::can_target_banner(gs, Banner::PeoplesFavor) {
                mask[encode_action(Action::CampaignTargetPeoplesFavor) as usize] = 1;
            }
            if campaign::can_target_banner(gs, Banner::DarkestSecret) {
                mask[encode_action(Action::CampaignTargetDarkestSecret) as usize] = 1;
            }
            if campaign::can_target_pawn(gs) {
                mask[encode_action(Action::CampaignTargetPawn) as usize] = 1;
            }
            if gs.campaign.as_ref().map_or(true, |c| !c.targets.is_empty()) {
                mask[encode_action(Action::Confirm) as usize] = 1;
            }
        }

        DecisionPoint::CampaignBattlePlan {
            player,
            is_attacker,
        } => {
            let bps = campaign::list_usable_battle_plans(gs, player, is_attacker);
            for i in 0..bps.len() {
                mask[encode_action(Action::CampaignUseBattlePlan(i as u8)) as usize] = 1;
            }
            mask[encode_action(Action::Decline) as usize] = 1; // Done with battle plans
        }

        DecisionPoint::CampaignSacrifice {
            min_needed,
            max_available,
            ..
        } => {
            mask[encode_action(Action::SelectAmount(0)) as usize] = 1; // Don't sacrifice (accept defeat)
            if min_needed <= max_available && min_needed <= 10 {
                mask[encode_action(Action::SelectAmount(min_needed)) as usize] = 1;
            }
        }

        DecisionPoint::CampaignPlaceWarbands { max_warbands, .. } => {
            for a in 0..=max_warbands.min(10) {
                mask[encode_action(Action::SelectAmount(a)) as usize] = 1;
            }
        }

        DecisionPoint::DealCompose { .. } => {
            if let Some(ref deal) = gs.deal {
                if deal.edits < 16 {
                let prop = deal.proposer;
                let resp = deal.responder;
                if deal.offer.favor < gs.players[prop as usize].favor {
                    mask[encode_action(Action::DealOfferFavorPlus) as usize] = 1;
                }
                if deal.offer.favor > 0 {
                    mask[encode_action(Action::DealOfferFavorMinus) as usize] = 1;
                }
                if deal.offer.secrets < gs.players[prop as usize].secrets_faceup {
                    mask[encode_action(Action::DealOfferSecretPlus) as usize] = 1;
                }
                if deal.offer.secrets > 0 {
                    mask[encode_action(Action::DealOfferSecretMinus) as usize] = 1;
                }
                if deal.request.favor < gs.players[resp as usize].favor {
                    mask[encode_action(Action::DealRequestFavorPlus) as usize] = 1;
                }
                if deal.request.favor > 0 {
                    mask[encode_action(Action::DealRequestFavorMinus) as usize] = 1;
                }
                if deal.request.secrets < gs.players[resp as usize].secrets_faceup {
                    mask[encode_action(Action::DealRequestSecretPlus) as usize] = 1;
                }
                if deal.request.secrets > 0 {
                    mask[encode_action(Action::DealRequestSecretMinus) as usize] = 1;
                }
                if deals::deal_allows_relics(deal.kind) {
                    for i in 0..gs.players[prop as usize].relics.len().min(3) {
                        if gs.players[prop as usize].relics[i] != CARD_GRAND_SCEPTER {
                            mask[encode_action(Action::DealToggleOfferRelic(i as u8)) as usize] = 1;
                        }
                    }
                    for i in 0..gs.players[resp as usize].relics.len().min(3) {
                        if gs.players[resp as usize].relics[i] != CARD_GRAND_SCEPTER {
                            mask[encode_action(Action::DealToggleRequestRelic(i as u8)) as usize] = 1;
                        }
                    }
                }
                if deals::deal_allows_advisers(deal.kind) {
                    for i in 0..MAX_ADVISERS {
                        if gs.players[prop as usize].advisers[i] != CARD_EMPTY {
                            mask[encode_action(Action::DealToggleOfferAdviser(i as u8)) as usize] = 1;
                        }
                        if gs.players[resp as usize].advisers[i] != CARD_EMPTY {
                            mask[encode_action(Action::DealToggleRequestAdviser(i as u8)) as usize] = 1;
                        }
                    }
                }
                if deal.kind == DealKind::Citizenship {
                    for i in 0..gs.reliquary.len().min(4) {
                        mask[encode_action(Action::DealSelectReliquary(i as u8)) as usize] = 1;
                    }
                    mask[encode_action(Action::DealToggleAllowPeek) as usize] = 1;
                }
                if deals::deal_allows_sites(deal.kind) {
                    if gs.count_sites_ruled(prop) > 0 {
                        mask[encode_action(Action::DealToggleOfferSite) as usize] = 1;
                    }
                    if gs.count_sites_ruled(resp) > 0 {
                        mask[encode_action(Action::DealToggleRequestSite) as usize] = 1;
                    }
                }
                if deals::deal_allows_contracts(deal.kind) && deal.contracts.len() < 2 {
                    mask[encode_action(Action::DealAddNonAggression) as usize] = 1;
                    mask[encode_action(Action::DealAddMustCampaignLeader) as usize] = 1;
                }
                if !deal.contracts.is_empty() {
                    mask[encode_action(Action::DealToggleContractPenalty) as usize] = 1;
                }
                }
            }
            mask[encode_action(Action::Confirm) as usize] = 1; // Submit offer
            mask[encode_action(Action::Decline) as usize] = 1; // Cancel deal
        }

        DecisionPoint::DealRespond { .. } => {
            mask[encode_action(Action::Confirm) as usize] = 1; // Accept
            mask[encode_action(Action::Decline) as usize] = 1; // Decline
            if gs.deal.as_ref().map_or(false, |d| d.round + 1 < MAX_DEAL_ROUNDS) {
                mask[encode_action(Action::DealCounterOffer) as usize] = 1;
            }
        }

        DecisionPoint::ReactiveTalk { player, .. } => {
            enable_talk_actions(gs, player, &mut mask);
            mask[encode_action(Action::PassTalk) as usize] = 1;
        }

        DecisionPoint::ChronicleVow { player } => {
            // Vision winner is locked to matching oath (§8.1)
            let locked = if gs.win_type == Some(WinType::Vision) {
                gs.players[player as usize]
                    .revealed_vision
                    .and_then(OathGoal::from_vision)
            } else {
                None
            };
            if let Some(g) = locked {
                mask[encode_action(Action::VowOath(g)) as usize] = 1;
            } else {
                for g in OathGoal::ALL {
                    if g != gs.oath_goal {
                        mask[encode_action(Action::VowOath(g)) as usize] = 1;
                    }
                }
            }
        }

        DecisionPoint::ChronicleEdifice { .. } => {
            mask[encode_action(Action::Confirm) as usize] = 1;
            mask[encode_action(Action::ChronicleSkip) as usize] = 1;
        }

        DecisionPoint::Terminal => {}
    }

    mask
}

fn enable_talk_actions(gs: &GameState, player: PlayerId, mask: &mut [i8; NUM_ACTIONS]) {
    for rel in 1..gs.num_players {
        mask[encode_action(Action::TalkProposeAlliance(rel)) as usize] = 1;
        mask[encode_action(Action::TalkRequestAttack(rel)) as usize] = 1;
        mask[encode_action(Action::TalkPledgeNonAggression(rel)) as usize] = 1;
    }
    if gs.players[player as usize].role == Role::Exile {
        mask[encode_action(Action::TalkRequestCitizenship) as usize] = 1;
    }
    mask[encode_action(Action::TalkAskForDeal) as usize] = 1;
    mask[encode_action(Action::TalkAcceptVerbal) as usize] = 1;
    mask[encode_action(Action::TalkRejectVerbal) as usize] = 1;
    for s in Suit::ALL {
        mask[encode_action(Action::TalkClaimSuit(s)) as usize] = 1;
    }
    for sl in 0..MAX_ADVISERS {
        if gs.players[player as usize].advisers[sl] != CARD_EMPTY
            && !gs.players[player as usize].adviser_faceup[sl]
        {
            mask[encode_action(Action::TalkShowAdviser(sl as u8)) as usize] = 1;
        }
    }
}

/// Apply one discrete `ActionId` to `GameState`.
/// Returns `Ok(())` on valid transition, or `Err(&'static str)` if invalid.
pub fn step(gs: &mut GameState, action_id: ActionId) -> Result<(), &'static str> {
    if gs.is_game_over {
        return Err("game is already over");
    }
    let Some(action) = decode_action(action_id) else {
        return Err("invalid action id");
    };
    let mask = legal_mask(gs);
    if mask[action_id as usize] == 0 {
        return Err("illegal action for current decision point");
    }
    gs.step_count += 1;

    match gs.decision.clone() {
        DecisionPoint::TurnAct { player } => match action {
            Action::Travel(si) => major_actions::execute_travel(gs, player, si, false),
            Action::SearchDeck => major_actions::execute_search(gs, player, true),
            Action::SearchDiscard => major_actions::execute_search(gs, player, false),
            Action::Muster(sl) => major_actions::execute_muster(gs, player, sl),
            Action::TradeFavor(sl) => major_actions::execute_trade_favor(gs, player, sl),
            Action::TradeSecrets(sl) => major_actions::execute_trade_secrets(gs, player, sl),
            Action::RecoverRelic(sl) => major_actions::execute_recover_relic(gs, player, sl),
            Action::RecoverPeoplesFavor => major_actions::execute_recover_peoples_favor(gs, player),
            Action::RecoverDarkestSecret => major_actions::execute_recover_darkest_secret(gs, player),
            Action::CampaignDeclare(rel) => {
                let target = resolve_rel_player(player, rel, gs.num_players);
                campaign::execute_campaign_declare(gs, player, Some(target));
            }
            Action::CampaignDeclareBandits => campaign::execute_campaign_declare(gs, player, None),
            Action::FlipAdviser(sl) => minor_actions::execute_flip_adviser(gs, player, sl),
            Action::DiscardAdviser(sl) => minor_actions::execute_discard_adviser(gs, player, sl),
            Action::UseCardAction(sl) => minor_actions::execute_use_card_action(gs, player, sl),
            Action::PeekSiteRelic(sl) => minor_actions::execute_peek_site_relic(gs, player, sl),
            Action::PeekReliquary => minor_actions::execute_peek_reliquary(gs, player),
            Action::MoveWarbandsToBoard => {
                gs.actions_taken_this_turn += 1;
                let site_idx = gs.players[player as usize].pawn_site;
                let max_mv = gs.sites[site_idx as usize].warbands.saturating_sub(1).min(10);
                gs.decision = DecisionPoint::ChooseAmount {
                    player,
                    reason: ChoiceReason::MoveWarbandsToBoard,
                    min: 1,
                    max: max_mv.max(1),
                };
            }
            Action::MoveWarbandsToSite => {
                gs.actions_taken_this_turn += 1;
                let max_mv = gs.players[player as usize].warbands_board.min(10);
                gs.decision = DecisionPoint::ChooseAmount {
                    player,
                    reason: ChoiceReason::MoveWarbandsToSite,
                    min: 1,
                    max: max_mv.max(1),
                };
            }
            Action::OfferCitizenship(rel) => {
                gs.actions_taken_this_turn += 1;
                let target = resolve_rel_player(player, rel, gs.num_players);
                minor_actions::execute_offer_citizenship(gs, player, target);
            }
            Action::ExileCitizen(rel) => {
                let target = resolve_rel_player(player, rel, gs.num_players);
                minor_actions::execute_exile_citizen(gs, player, target);
            }
            Action::SelfExile => minor_actions::execute_self_exile(gs, player),
            Action::EndActPhase => turn::do_rest_phase(gs),
            other => {
                deals::handle_talk_action(gs, player, other);
            }
        },

        DecisionPoint::SearchResolve { player } => match action {
            Action::SearchPlay { card_idx, dest } => {
                major_actions::execute_search_play(gs, player, card_idx, dest);
            }
            Action::SearchDiscardCard(card_idx) => {
                major_actions::execute_search_discard(gs, player, card_idx);
            }
            _ => {
                gs.search = None;
                gs.decision = DecisionPoint::TurnAct { player };
            }
        },

        DecisionPoint::ChooseSite { player, reason, .. } => {
            if let Action::SelectSite(si) = action {
                match reason {
                    ChoiceReason::BanishDestination => {
                        if let Some(PendingEffect::ResumeCampaignBanish { defender }) = gs.effect_stack.pop() {
                            campaign::execute_banish_travel(gs, defender, si);
                        } else {
                            campaign::finish_campaign(gs);
                        }
                    }
                    ChoiceReason::CardTargetSite => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, step: st, aux }) =
                            gs.effect_stack.pop()
                        {
                            cards::denizens::resume_card_site_choice(gs, cp, card_id, st, aux, si);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            } else {
                gs.effect_stack.pop();
                gs.decision = DecisionPoint::TurnAct { player: gs.current_player };
            }
        }

        DecisionPoint::ChooseSiteCard { player, site, reason, .. } => {
            if let Action::SelectSlot(sl) = action {
                match reason {
                    ChoiceReason::DiscardSiteCard => {
                        let old = gs.sites[site as usize].cards[sl as usize];
                        if old != CARD_EMPTY {
                            let dest = gs.sites[site as usize].region.discard_target();
                            gs.discard_piles[dest as usize].push(old);
                            gs.sites[site as usize].cards[sl as usize] = CARD_EMPTY;
                        }
                        if let Some(PendingEffect::ResumeSearchPlay { player: sp, card_id, .. }) =
                            gs.effect_stack.pop()
                        {
                            gs.sites[site as usize].cards[sl as usize] = card_id;
                            major_actions::on_card_played_to_site(gs, sp, site, card_id);
                            gs.decision = DecisionPoint::TurnAct { player: sp };
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    ChoiceReason::CardTargetSiteCard => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, step: st, aux }) =
                            gs.effect_stack.pop()
                        {
                            cards::denizens::resume_card_slot_choice(gs, cp, card_id, st, aux, sl);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            } else {
                gs.effect_stack.pop();
                gs.decision = DecisionPoint::TurnAct { player };
            }
        }

        DecisionPoint::ChooseAdviser { player, owner, reason, .. } => {
            if let Action::SelectSlot(sl) = action {
                match reason {
                    ChoiceReason::ReplaceAdviser => {
                        minor_actions::execute_discard_adviser(gs, owner, sl);
                        if let Some(PendingEffect::ResumeSearchPlay { player: sp, card_id, dest }) =
                            gs.effect_stack.pop()
                        {
                            major_actions::place_played_card(gs, sp, card_id, dest);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    ChoiceReason::CardTargetAdviser => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, step: st, aux }) =
                            gs.effect_stack.pop()
                        {
                            cards::denizens::resume_card_slot_choice(gs, cp, card_id, st, aux, sl);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            } else {
                gs.effect_stack.pop();
                gs.decision = DecisionPoint::TurnAct { player };
            }
        }

        DecisionPoint::ChooseSuit { player, reason, .. } => {
            if let Action::SelectSuit(suit) = action {
                match reason {
                    ChoiceReason::CardGainFavorBank => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, step: st, aux }) =
                            gs.effect_stack.pop()
                        {
                            cards::denizens::resume_card_suit_choice(gs, cp, card_id, st, aux, suit);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            }
        }

        DecisionPoint::ChoosePlayer { player, reason, .. } => {
            if let Action::SelectRelPlayer(rel) = action {
                let target = resolve_rel_player(player, rel, gs.num_players);
                match reason {
                    ChoiceReason::DealPartner => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, .. }) =
                            gs.effect_stack.pop()
                        {
                            let kind = match card_id {
                                13 => DealKind::TinkersFair,
                                27 => DealKind::TheGathering,
                                146 => DealKind::DeedWriter,
                                EDIFICE_FESTIVAL_DISTRICT => DealKind::FestivalDistrict,
                                SITE_THE_TRIBUNAL => DealKind::TheTribunal,
                                _ => DealKind::TinkersFair,
                            };
                            deals::start_deal(gs, kind, cp, target);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    ChoiceReason::CardTargetPlayer => {
                        if let Some(PendingEffect::ResumeCardEffect { card_id, player: cp, step: st, aux }) =
                            gs.effect_stack.pop()
                        {
                            cards::denizens::resume_card_player_choice(gs, cp, card_id, st, aux, target);
                        } else {
                            gs.decision = DecisionPoint::TurnAct { player };
                        }
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            } else {
                gs.effect_stack.pop();
                gs.decision = DecisionPoint::TurnAct { player };
            }
        }

        DecisionPoint::ChooseAmount { player, reason, .. } => {
            if let Action::SelectAmount(amt) = action {
                match reason {
                    ChoiceReason::MoveWarbandsToBoard => {
                        minor_actions::execute_move_warbands_to_board(gs, player, amt);
                        gs.decision = DecisionPoint::TurnAct { player };
                    }
                    ChoiceReason::MoveWarbandsToSite => {
                        minor_actions::execute_move_warbands_to_site(gs, player, amt);
                        gs.decision = DecisionPoint::TurnAct { player };
                    }
                    _ => gs.decision = DecisionPoint::TurnAct { player },
                }
            }
        }

        DecisionPoint::ChooseYesNo { player, reason, .. } => {
            let yes = action == Action::Confirm;
            match reason {
                ChoiceReason::SiteWakeResource => {
                    let si = gs.players[player as usize].pawn_site as usize;
                    if yes && gs.sites[si].site_secrets > 0 {
                        gs.sites[si].site_secrets -= 1;
                        gs.players[player as usize].secrets_faceup += 1;
                    } else if gs.sites[si].site_favor > 0 {
                        gs.sites[si].site_favor -= 1;
                        gs.players[player as usize].favor += 1;
                    }
                    if let Some(PendingEffect::ResumeWakePhase { player: wp, step: st }) = gs.effect_stack.pop() {
                        turn::resume_wake_phase(gs, wp, st);
                    }
                }
                ChoiceReason::SqualidDistrictRoll => {
                    if let Some(PendingEffect::ResumeEndOfRoundCheck { roll }) = gs.effect_stack.pop() {
                        let adj = if yes { (roll + 1).min(6) } else { roll.saturating_sub(1).max(1) };
                        turn::finish_end_of_round(gs, adj);
                    }
                }
                ChoiceReason::DowsingSticksKeep => {
                    if let Some(PendingEffect::ResumeCardEffect { aux: relic_id, player: cp, .. }) =
                        gs.effect_stack.pop()
                    {
                        if yes {
                            gs.players[cp as usize].relics.push(relic_id);
                            win::recalculate_oathkeeper(gs);
                        } else {
                            gs.relic_deck.insert(0, relic_id);
                        }
                    }
                    gs.decision = DecisionPoint::TurnAct { player: gs.current_player };
                }
                _ => {
                    gs.effect_stack.pop();
                    gs.decision = DecisionPoint::TurnAct { player: gs.current_player };
                }
            }
        }

        DecisionPoint::CampaignTargets { .. } => match action {
            Action::SelectSite(si) => campaign::execute_target_site(gs, si),
            Action::CampaignTargetRelic(sl) => campaign::execute_target_relic(gs, sl),
            Action::CampaignTargetPeoplesFavor => campaign::execute_target_banner(gs, Banner::PeoplesFavor),
            Action::CampaignTargetDarkestSecret => campaign::execute_target_banner(gs, Banner::DarkestSecret),
            Action::CampaignTargetPawn => campaign::execute_target_pawn(gs),
            Action::Confirm => campaign::execute_done_targets(gs),
            _ => {}
        },

        DecisionPoint::CampaignBattlePlan { player, is_attacker } => match action {
            Action::CampaignUseBattlePlan(sl) => {
                campaign::execute_use_battle_plan(gs, player, is_attacker, sl);
            }
            _ => campaign::execute_done_battle_plans(gs, is_attacker),
        },

        DecisionPoint::CampaignSacrifice { .. } => {
            if let Action::SelectAmount(amt) = action {
                campaign::execute_campaign_sacrifice(gs, amt);
            }
        }

        DecisionPoint::CampaignPlaceWarbands { .. } => {
            if let Action::SelectAmount(amt) = action {
                campaign::execute_place_warbands(gs, amt);
            }
        }

        DecisionPoint::CampaignBanishBurn { defender, .. } => {
            campaign::execute_banish_burn(gs, defender, action == Action::Confirm);
        }

        DecisionPoint::DealCompose { .. } => deals::handle_deal_compose_action(gs, action),
        DecisionPoint::DealRespond { .. } => deals::handle_deal_respond_action(gs, action),

        DecisionPoint::ReactiveTalk { player, .. } => {
            if action != Action::PassTalk {
                deals::handle_talk_action(gs, player, action);
            }
            match gs.effect_stack.pop() {
                Some(PendingEffect::ResumeCampaignAfterReactiveTalk) => {
                    campaign::resume_campaign_after_reactive_talk(gs);
                }
                Some(PendingEffect::ResumeDealAfterReactiveTalk) => {
                    let resp = gs.deal.as_ref().map(|d| d.responder).unwrap_or(gs.current_player);
                    gs.decision = DecisionPoint::DealRespond { player: resp };
                }
                _ => {
                    gs.decision = DecisionPoint::TurnAct { player: gs.current_player };
                }
            }
        }

        DecisionPoint::ChronicleVow { .. } => {
            if let Action::VowOath(goal) = action {
                gs.vowed_oath = Some(goal);
                gs.is_game_over = true;
                gs.phase = Phase::GameOver;
                gs.decision = DecisionPoint::Terminal;
            }
        }

        DecisionPoint::ChronicleEdifice { .. } => {
            gs.is_game_over = true;
            gs.phase = Phase::GameOver;
            gs.decision = DecisionPoint::Terminal;
        }

        DecisionPoint::Terminal => {}
    }

    // Safety cap to prevent infinite minor-action/talk loops in random fuzzing
    if !gs.is_game_over && gs.step_count > 5000 {
        win::declare_empire_win(gs);
        gs.is_game_over = true;
        gs.phase = Phase::GameOver;
        gs.decision = DecisionPoint::Terminal;
    }

    Ok(())
}

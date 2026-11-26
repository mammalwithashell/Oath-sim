use smallvec::SmallVec;

use crate::actions::{resolve_rel_player, Action};
use crate::cards::get_card;
use crate::engine::minor_actions::convert_exile_to_citizen;
use crate::engine::turn::do_rest_phase;
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

// ── BINDING DEAL BUILDER ──────────────────────────────────────────────────

pub fn start_deal(gs: &mut GameState, kind: DealKind, initiator: PlayerId, partner: PlayerId) {
    let mut offer = DealBundle::default();
    if kind == DealKind::Citizenship && !gs.reliquary.is_empty() {
        offer.reliquary_slot = Some(0);
    }
    gs.deal = Some(DealState {
        kind,
        initiator,
        proposer: initiator,
        responder: partner,
        round: 0,
        edits: 0,
        offer,
        request: DealBundle::default(),
        contracts: SmallVec::new(),
        allow_reliquary_peek: false,
    });
    gs.decision = DecisionPoint::DealCompose { player: initiator };
}

pub fn deal_allows_relics(kind: DealKind) -> bool {
    matches!(
        kind,
        DealKind::Citizenship | DealKind::TinkersFair | DealKind::TheGathering
    )
}

pub fn deal_allows_advisers(kind: DealKind) -> bool {
    matches!(kind, DealKind::TheGathering | DealKind::FestivalDistrict)
}

pub fn deal_allows_sites(kind: DealKind) -> bool {
    matches!(kind, DealKind::DeedWriter)
}

pub fn deal_allows_contracts(kind: DealKind) -> bool {
    matches!(kind, DealKind::TheTribunal)
}

pub fn handle_deal_compose_action(gs: &mut GameState, action: Action) {
    let Some(mut deal) = gs.deal.clone() else {
        gs.decision = DecisionPoint::TurnAct {
            player: gs.current_player,
        };
        return;
    };
    let prop = deal.proposer;
    let resp = deal.responder;

    match action {
        Action::DealOfferFavorPlus => {
            if deal.offer.favor < gs.players[prop as usize].favor {
                deal.offer.favor += 1;
            }
        }
        Action::DealOfferFavorMinus => {
            deal.offer.favor = deal.offer.favor.saturating_sub(1);
        }
        Action::DealOfferSecretPlus => {
            if deal.offer.secrets < gs.players[prop as usize].secrets_faceup {
                deal.offer.secrets += 1;
            }
        }
        Action::DealOfferSecretMinus => {
            deal.offer.secrets = deal.offer.secrets.saturating_sub(1);
        }
        Action::DealRequestFavorPlus => {
            if deal.request.favor < gs.players[resp as usize].favor {
                deal.request.favor += 1;
            }
        }
        Action::DealRequestFavorMinus => {
            deal.request.favor = deal.request.favor.saturating_sub(1);
        }
        Action::DealRequestSecretPlus => {
            if deal.request.secrets < gs.players[resp as usize].secrets_faceup {
                deal.request.secrets += 1;
            }
        }
        Action::DealRequestSecretMinus => {
            deal.request.secrets = deal.request.secrets.saturating_sub(1);
        }
        Action::DealToggleOfferRelic(idx) => {
            if deal_allows_relics(deal.kind) {
                if let Some(&rid) = gs.players[prop as usize].relics.get(idx as usize) {
                    if rid != CARD_GRAND_SCEPTER {
                        if let Some(pos) = deal.offer.relics.iter().position(|&r| r == rid) {
                            deal.offer.relics.remove(pos);
                        } else {
                            deal.offer.relics.push(rid);
                        }
                    }
                }
            }
        }
        Action::DealToggleRequestRelic(idx) => {
            if deal_allows_relics(deal.kind) {
                if let Some(&rid) = gs.players[resp as usize].relics.get(idx as usize) {
                    if rid != CARD_GRAND_SCEPTER {
                        if let Some(pos) = deal.request.relics.iter().position(|&r| r == rid) {
                            deal.request.relics.remove(pos);
                        } else {
                            deal.request.relics.push(rid);
                        }
                    }
                }
            }
        }
        Action::DealToggleOfferAdviser(slot) => {
            if deal_allows_advisers(deal.kind)
                && (slot as usize) < MAX_ADVISERS
                && gs.players[prop as usize].advisers[slot as usize] != CARD_EMPTY
            {
                if let Some(pos) = deal.offer.advisers.iter().position(|&s| s == slot) {
                    deal.offer.advisers.remove(pos);
                } else {
                    deal.offer.advisers.push(slot);
                }
            }
        }
        Action::DealToggleRequestAdviser(slot) => {
            if deal_allows_advisers(deal.kind)
                && (slot as usize) < MAX_ADVISERS
                && gs.players[resp as usize].advisers[slot as usize] != CARD_EMPTY
            {
                if let Some(pos) = deal.request.advisers.iter().position(|&s| s == slot) {
                    deal.request.advisers.remove(pos);
                } else {
                    deal.request.advisers.push(slot);
                }
            }
        }
        Action::DealSelectReliquary(slot) => {
            if deal.kind == DealKind::Citizenship && (slot as usize) < gs.reliquary.len() {
                deal.offer.reliquary_slot = Some(slot);
            }
        }
        Action::DealToggleAllowPeek => {
            if deal.kind == DealKind::Citizenship {
                deal.allow_reliquary_peek = !deal.allow_reliquary_peek;
            }
        }
        Action::DealToggleOfferSite => {
            if deal_allows_sites(deal.kind) {
                if let Some(si) = (0..MAX_SITES as u8).find(|&s| gs.player_rules_site(prop, s)) {
                    if let Some(pos) = deal.offer.sites.iter().position(|&s| s == si) {
                        deal.offer.sites.remove(pos);
                    } else {
                        deal.offer.sites.push(si);
                    }
                }
            }
        }
        Action::DealToggleRequestSite => {
            if deal_allows_sites(deal.kind) {
                if let Some(si) = (0..MAX_SITES as u8).find(|&s| gs.player_rules_site(resp, s)) {
                    if let Some(pos) = deal.request.sites.iter().position(|&s| s == si) {
                        deal.request.sites.remove(pos);
                    } else {
                        deal.request.sites.push(si);
                    }
                }
            }
        }
        Action::DealAddNonAggression => {
            if deal_allows_contracts(deal.kind) && deal.contracts.len() < 2 {
                let until = (gs.round_number + 2).min(MAX_ROUNDS);
                deal.contracts.push(TribunalContract {
                    party_a: prop,
                    party_b: resp,
                    clause: ContractClause::NonAggression {
                        actor: resp,
                        target: prop,
                        until_round: until,
                    },
                    enforcement: EnforcementMode::HardEnforced,
                    fulfilled: false,
                });
            }
        }
        Action::DealAddMustCampaignLeader => {
            if deal_allows_contracts(deal.kind) && deal.contracts.len() < 2 {
                let leader = gs.oathkeeper_holder.unwrap_or(0);
                if leader != resp {
                    let by = (gs.round_number + 1).min(MAX_ROUNDS);
                    deal.contracts.push(TribunalContract {
                        party_a: prop,
                        party_b: resp,
                        clause: ContractClause::MustCampaign {
                            actor: resp,
                            target: leader,
                            by_round: by,
                        },
                        enforcement: EnforcementMode::PenaltyOnBreach {
                            favor: 2,
                            secrets: 0,
                        },
                        fulfilled: false,
                    });
                }
            }
        }
        Action::DealToggleContractPenalty => {
            if let Some(last) = deal.contracts.last_mut() {
                last.enforcement = match last.enforcement {
                    EnforcementMode::HardEnforced => EnforcementMode::PenaltyOnBreach {
                        favor: 2,
                        secrets: 1,
                    },
                    EnforcementMode::PenaltyOnBreach { .. } => EnforcementMode::HardEnforced,
                };
            }
        }
        // Submit Offer -> reactive talk window for responder, then DealRespond
        Action::Confirm => {
            if deal.allow_reliquary_peek {
                for sl in 0..gs.reliquary.len() {
                    gs.knowledge[resp as usize].mark_reliquary_known(sl);
                }
            }
            let ctx = if deal.kind == DealKind::Citizenship {
                ReactiveContext::CitizenshipOffer
            } else {
                ReactiveContext::DealResponse
            };
            gs.deal = Some(deal);
            gs.effect_stack
                .push(PendingEffect::ResumeDealAfterReactiveTalk);
            gs.decision = DecisionPoint::ReactiveTalk {
                player: resp,
                context: ctx,
            };
            return;
        }
        // Cancel Deal
        Action::Decline => {
            gs.deal = None;
            gs.decision = DecisionPoint::TurnAct {
                player: gs.current_player,
            };
            return;
        }
        _ => {}
    }

    deal.edits = deal.edits.saturating_add(1);
    gs.deal = Some(deal);
}

pub fn handle_deal_respond_action(gs: &mut GameState, action: Action) {
    let Some(deal) = gs.deal.clone() else {
        gs.decision = DecisionPoint::TurnAct {
            player: gs.current_player,
        };
        return;
    };

    match action {
        Action::Confirm => {
            execute_accepted_deal(gs, &deal);
            gs.deal = None;
            if deal.kind == DealKind::Citizenship {
                // Accepting Citizenship ends the accepting player's next act / or current turn if appropriate
                gs.decision = DecisionPoint::TurnAct {
                    player: gs.current_player,
                };
            } else {
                gs.decision = DecisionPoint::TurnAct {
                    player: gs.current_player,
                };
            }
        }
        Action::DealCounterOffer if deal.round + 1 < MAX_DEAL_ROUNDS => {
            // Swap proposer and responder; swap offer and request trays
            let mut countered = deal.clone();
            countered.proposer = deal.responder;
            countered.responder = deal.proposer;
            countered.offer = deal.request;
            countered.request = deal.offer;
            countered.round += 1;
            countered.edits = 0;
            let next_player = countered.proposer;
            gs.deal = Some(countered);
            gs.decision = DecisionPoint::DealCompose {
                player: next_player,
            };
        }
        _ => {
            // Declined
            gs.deal = None;
            gs.decision = DecisionPoint::TurnAct {
                player: gs.current_player,
            };
        }
    }
}

fn execute_accepted_deal(gs: &mut GameState, deal: &DealState) {
    let p = deal.proposer;
    let r = deal.responder;

    // 1. Transfer Favor & Secrets atomically
    let p_fav = deal.offer.favor.min(gs.players[p as usize].favor);
    let r_fav = deal.request.favor.min(gs.players[r as usize].favor);
    gs.players[p as usize].favor = gs.players[p as usize].favor - p_fav + r_fav;
    gs.players[r as usize].favor = gs.players[r as usize].favor - r_fav + p_fav;

    let p_sec = deal.offer.secrets.min(gs.players[p as usize].secrets_faceup);
    let r_sec = deal.request.secrets.min(gs.players[r as usize].secrets_faceup);
    gs.players[p as usize].secrets_faceup = gs.players[p as usize].secrets_faceup - p_sec + r_sec;
    gs.players[r as usize].secrets_faceup = gs.players[r as usize].secrets_faceup - r_sec + p_sec;

    // 2. Transfer Relics
    for &rid in &deal.offer.relics {
        if let Some(pos) = gs.players[p as usize].relics.iter().position(|&x| x == rid) {
            gs.players[p as usize].relics.remove(pos);
            gs.players[r as usize].relics.push(rid);
        }
    }
    for &rid in &deal.request.relics {
        if let Some(pos) = gs.players[r as usize].relics.iter().position(|&x| x == rid) {
            gs.players[r as usize].relics.remove(pos);
            gs.players[p as usize].relics.push(rid);
        }
    }

    // 3. Transfer Advisers (swap/move into empty slots)
    for &sl in &deal.offer.advisers {
        let cid = gs.players[p as usize].advisers[sl as usize];
        if cid != CARD_EMPTY {
            if let Some(dst) = gs.players[r as usize].first_empty_adviser() {
                let fu = gs.players[p as usize].adviser_faceup[sl as usize];
                gs.players[p as usize].advisers[sl as usize] = CARD_EMPTY;
                gs.players[p as usize].adviser_faceup[sl as usize] = false;
                gs.players[r as usize].advisers[dst] = cid;
                gs.players[r as usize].adviser_faceup[dst] = fu;
            }
        }
    }
    for &sl in &deal.request.advisers {
        let cid = gs.players[r as usize].advisers[sl as usize];
        if cid != CARD_EMPTY {
            if let Some(dst) = gs.players[p as usize].first_empty_adviser() {
                let fu = gs.players[r as usize].adviser_faceup[sl as usize];
                gs.players[r as usize].advisers[sl as usize] = CARD_EMPTY;
                gs.players[r as usize].adviser_faceup[sl as usize] = false;
                gs.players[p as usize].advisers[dst] = cid;
                gs.players[p as usize].adviser_faceup[dst] = fu;
            }
        }
    }

    // 4. Transfer Ruled Sites (Deed Writer OATH-146)
    for &si in &deal.offer.sites {
        transfer_site_rule(gs, p, r, si);
    }
    for &si in &deal.request.sites {
        transfer_site_rule(gs, r, p, si);
    }

    // 5. Citizenship: grant Reliquary relic & flip Exile -> Citizen
    if deal.kind == DealKind::Citizenship {
        let exile = if gs.players[r as usize].role == Role::Exile {
            r
        } else {
            p
        };
        let slot = deal
            .offer
            .reliquary_slot
            .or(deal.request.reliquary_slot)
            .unwrap_or(0) as usize;
        if slot < gs.reliquary.len() {
            let rid = gs.reliquary.remove(slot);
            gs.players[exile as usize].relics.push(rid);
        }
        convert_exile_to_citizen(gs, exile);
        if exile == gs.current_player {
            do_rest_phase(gs);
        }
    }

    // 6. Activate Tribunal Contracts
    for c in &deal.contracts {
        if gs.active_contracts.len() < 6 {
            gs.active_contracts.push(c.clone());
        }
    }

    recalculate_oathkeeper(gs);
}

fn transfer_site_rule(gs: &mut GameState, from: PlayerId, to: PlayerId, si: SiteIndex) {
    if !gs.player_rules_site(from, si) {
        return;
    }
    let old_wb = gs.sites[si as usize].warbands;
    gs.players[from as usize].warbands_board += old_wb;
    let new_wb = gs.players[to as usize].warbands_board.min(1);
    gs.players[to as usize].warbands_board -= new_wb;
    if new_wb > 0 {
        gs.sites[si as usize].warbands = new_wb;
        gs.sites[si as usize].ruling_player = Some(to);
        gs.sites[si as usize].warband_color = Some(if gs.is_imperial(to) { 0 } else { to });
    } else {
        gs.sites[si as usize].warbands = 0;
        gs.sites[si as usize].ruling_player = None;
        gs.sites[si as usize].warband_color = None;
    }
}

// ── TRIBUNAL CONTRACT ENFORCEMENT ─────────────────────────────────────────

pub fn is_campaign_blocked_by_contract(gs: &GameState, attacker: PlayerId, defender: PlayerId) -> bool {
    gs.active_contracts.iter().any(|c| {
        !c.fulfilled
            && matches!(c.enforcement, EnforcementMode::HardEnforced)
            && matches!(
                c.clause,
                ContractClause::NonAggression { actor, target, until_round }
                if actor == attacker && target == defender && gs.round_number <= until_round
            )
    })
}

pub fn check_contract_violation_banner(gs: &GameState, actor_p: PlayerId, banner: Banner) -> bool {
    gs.active_contracts.iter().any(|c| {
        !c.fulfilled
            && matches!(c.enforcement, EnforcementMode::HardEnforced)
            && matches!(
                c.clause,
                ContractClause::MustNotRecoverBanner { actor, banner: b, until_round }
                if actor == actor_p && b == banner && gs.round_number <= until_round
            )
    })
}

pub fn on_campaign_declared_contracts(gs: &mut GameState, attacker: PlayerId, defender: PlayerId) {
    let mut penalties: SmallVec<[(PlayerId, PlayerId, u8, u8); 4]> = SmallVec::new();
    for c in &mut gs.active_contracts {
        if c.fulfilled {
            continue;
        }
        match c.clause {
            ContractClause::MustCampaign {
                actor,
                target,
                by_round,
            } if actor == attacker && target == defender && gs.round_number <= by_round => {
                c.fulfilled = true;
            }
            ContractClause::NonAggression {
                actor,
                target,
                until_round,
            } if actor == attacker && target == defender && gs.round_number <= until_round => {
                if let EnforcementMode::PenaltyOnBreach { favor, secrets } = c.enforcement {
                    let other = if c.party_a == actor { c.party_b } else { c.party_a };
                    penalties.push((actor, other, favor, secrets));
                    c.fulfilled = true;
                }
            }
            _ => {}
        }
    }
    for (breacher, victim, fav, sec) in penalties {
        apply_breach_penalty(gs, breacher, victim, fav, sec);
    }
}

pub fn check_contract_deadlines(gs: &mut GameState, ending_player: PlayerId) {
    let mut penalties: SmallVec<[(PlayerId, PlayerId, u8, u8); 4]> = SmallVec::new();
    for c in &mut gs.active_contracts {
        if c.fulfilled {
            continue;
        }
        if let ContractClause::MustCampaign {
            actor,
            by_round,
            ..
        } = c.clause
        {
            if actor == ending_player && gs.round_number >= by_round {
                if let EnforcementMode::PenaltyOnBreach { favor, secrets } = c.enforcement {
                    let other = if c.party_a == actor { c.party_b } else { c.party_a };
                    penalties.push((actor, other, favor, secrets));
                }
                c.fulfilled = true;
            }
        }
    }
    for (breacher, victim, fav, sec) in penalties {
        apply_breach_penalty(gs, breacher, victim, fav, sec);
    }
    gs.active_contracts.retain(|c| !c.fulfilled);
}

fn apply_breach_penalty(
    gs: &mut GameState,
    breacher: PlayerId,
    victim: PlayerId,
    favor: u8,
    secrets: u8,
) {
    let f = favor.min(gs.players[breacher as usize].favor);
    gs.players[breacher as usize].favor -= f;
    gs.players[victim as usize].favor += f;

    let s = secrets.min(gs.players[breacher as usize].secrets_faceup);
    gs.players[breacher as usize].secrets_faceup -= s;
    gs.players[victim as usize].secrets_faceup += s;
}

// ── STRUCTURED TABLE TALK & MECHANICAL CARD SHOWING ───────────────────────

pub fn handle_talk_action(gs: &mut GameState, sender: PlayerId, action: Action) -> bool {
    let n = gs.num_players;
    let event = match action {
        Action::TalkProposeAlliance(rel) => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: Some(resolve_rel_player(sender, rel, n)),
            intent: TalkIntent::ProposeAlliance,
            suit: None,
            shown_card: None,
        }),
        Action::TalkRequestAttack(rel) => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: Some(resolve_rel_player(sender, rel, n)),
            intent: TalkIntent::RequestAttack,
            suit: None,
            shown_card: None,
        }),
        Action::TalkPledgeNonAggression(rel) => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: Some(resolve_rel_player(sender, rel, n)),
            intent: TalkIntent::PledgeNonAggression,
            suit: None,
            shown_card: None,
        }),
        Action::TalkRequestCitizenship => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: Some(gs.chancellor_index()),
            intent: TalkIntent::RequestCitizenship,
            suit: None,
            shown_card: None,
        }),
        Action::TalkAskForDeal => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: None,
            intent: TalkIntent::AskForDeal,
            suit: None,
            shown_card: None,
        }),
        Action::TalkAcceptVerbal => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: None,
            intent: TalkIntent::AcceptVerbal,
            suit: None,
            shown_card: None,
        }),
        Action::TalkRejectVerbal => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: None,
            intent: TalkIntent::RejectVerbal,
            suit: None,
            shown_card: None,
        }),
        Action::TalkClaimSuit(suit) => Some(TalkEvent {
            round: gs.round_number,
            sender,
            target: None,
            intent: TalkIntent::ClaimSuit,
            suit: Some(suit),
            shown_card: None,
        }),
        Action::TalkShowAdviser(slot) => {
            let cid = gs.players[sender as usize].advisers[slot as usize];
            if cid != CARD_EMPTY && !gs.players[sender as usize].adviser_faceup[slot as usize] {
                // Reveal true CardId to all other players' KnowledgeState (§9.4)
                for p in 0..n {
                    if p != sender {
                        gs.knowledge[p as usize].mark_adviser_known(sender, slot as usize);
                    }
                }
                Some(TalkEvent {
                    round: gs.round_number,
                    sender,
                    target: None,
                    intent: TalkIntent::ShowedAdviser,
                    suit: get_card(cid).suit,
                    shown_card: Some(cid),
                })
            } else {
                None
            }
        }
        _ => None,
    };

    if let Some(ev) = event {
        gs.push_talk(ev);
        if matches!(gs.decision, DecisionPoint::TurnAct { .. }) {
            gs.players[sender as usize].talk_remaining =
                gs.players[sender as usize].talk_remaining.saturating_sub(1);
        }
        true
    } else {
        false
    }
}

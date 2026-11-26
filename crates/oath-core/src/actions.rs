use crate::cards::get_card;
use crate::state::GameState;
use crate::types::*;

pub const NUM_ACTIONS: usize = 216;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    // Major actions (TurnAct)
    Travel(SiteIndex),
    SearchDeck,
    SearchDiscard,
    Muster(u8),
    TradeFavor(u8),
    TradeSecrets(u8),
    RecoverRelic(u8),
    RecoverPeoplesFavor,
    RecoverDarkestSecret,
    CampaignDeclare(u8), // relative player offset 1..=5
    CampaignDeclareBandits,

    // Minor actions (TurnAct)
    FlipAdviser(u8),
    DiscardAdviser(u8),
    UseCardAction(u8), // 0..3 site cards, 3..6 advisers, 6 site power, 7..11 relics 0..4
    PeekSiteRelic(u8),
    PeekReliquary,
    MoveWarbandsToBoard,
    MoveWarbandsToSite,
    OfferCitizenship(u8), // relative player offset 1..=5
    ExileCitizen(u8),     // relative player offset 1..=5
    SelfExile,
    EndActPhase,

    // Generic sub-choices (context-gated)
    SelectSite(SiteIndex),
    SelectSlot(u8), // 0..=3
    SelectRelPlayer(u8), // 0..=5
    SelectSuit(Suit),
    SelectAmount(u8), // 0..=10
    Confirm,
    Decline,

    // Search resolution
    SearchPlay { card_idx: u8, dest: u8 }, // dest: 0=site, 1=adviser_up, 2=adviser_down, 3=vision
    SearchDiscardCard(u8),

    // Campaign sub-actions
    CampaignTargetRelic(u8),
    CampaignTargetPeoplesFavor,
    CampaignTargetDarkestSecret,
    CampaignTargetPawn,
    CampaignUseBattlePlan(u8),

    // Chronicle / Vow
    VowOath(OathGoal),

    // Deal & Tribunal Contract Builder
    DealOfferFavorPlus,
    DealOfferFavorMinus,
    DealOfferSecretPlus,
    DealOfferSecretMinus,
    DealRequestFavorPlus,
    DealRequestFavorMinus,
    DealRequestSecretPlus,
    DealRequestSecretMinus,
    DealToggleOfferRelic(u8),
    DealToggleRequestRelic(u8),
    DealToggleOfferAdviser(u8),
    DealToggleRequestAdviser(u8),
    DealSelectReliquary(u8),
    DealToggleAllowPeek,
    DealCounterOffer,
    DealAddNonAggression,
    DealAddMustCampaignLeader,
    DealToggleContractPenalty,
    DealToggleOfferSite,
    DealToggleRequestSite,

    // Table Talk & Mechanical Card Showing
    TalkProposeAlliance(u8), // rel_player 1..=5
    TalkRequestAttack(u8),
    TalkPledgeNonAggression(u8),
    TalkRequestCitizenship,
    TalkAskForDeal,
    TalkAcceptVerbal,
    TalkRejectVerbal,
    TalkClaimSuit(Suit),
    TalkShowAdviser(u8), // slot 0..=2
    PassTalk,
    ChronicleSkip,
}

pub fn decode_action(id: ActionId) -> Option<Action> {
    match id {
        0..=7 => Some(Action::Travel(id as u8)),
        8 => Some(Action::SearchDeck),
        9 => Some(Action::SearchDiscard),
        10..=12 => Some(Action::Muster((id - 10) as u8)),
        13..=15 => Some(Action::TradeFavor((id - 13) as u8)),
        16..=18 => Some(Action::TradeSecrets((id - 16) as u8)),
        19..=21 => Some(Action::RecoverRelic((id - 19) as u8)),
        22 => Some(Action::RecoverPeoplesFavor),
        23 => Some(Action::RecoverDarkestSecret),
        24..=28 => Some(Action::CampaignDeclare((id - 24 + 1) as u8)),
        29 => Some(Action::CampaignDeclareBandits),
        30..=32 => Some(Action::FlipAdviser((id - 30) as u8)),
        33..=35 => Some(Action::DiscardAdviser((id - 33) as u8)),
        36..=46 => Some(Action::UseCardAction((id - 36) as u8)),
        47..=49 => Some(Action::PeekSiteRelic((id - 47) as u8)),
        50 => Some(Action::PeekReliquary),
        51 => Some(Action::MoveWarbandsToBoard),
        52 => Some(Action::MoveWarbandsToSite),
        53..=57 => Some(Action::OfferCitizenship((id - 53 + 1) as u8)),
        58..=62 => Some(Action::ExileCitizen((id - 58 + 1) as u8)),
        63 => Some(Action::SelfExile),
        64 => Some(Action::EndActPhase),
        65..=72 => Some(Action::SelectSite((id - 65) as u8)),
        73..=76 => Some(Action::SelectSlot((id - 73) as u8)),
        77..=82 => Some(Action::SelectRelPlayer((id - 77) as u8)),
        83..=88 => Suit::from_u8((id - 83) as u8).map(Action::SelectSuit),
        89..=99 => Some(Action::SelectAmount((id - 89) as u8)),
        100 => Some(Action::Confirm),
        101 => Some(Action::Decline),
        102..=125 => {
            let off = (id - 102) as u8;
            Some(Action::SearchPlay {
                card_idx: off / 4,
                dest: off % 4,
            })
        }
        126..=131 => Some(Action::SearchDiscardCard((id - 126) as u8)),
        132..=137 => Some(Action::CampaignTargetRelic((id - 132) as u8)),
        138 => Some(Action::CampaignTargetPeoplesFavor),
        139 => Some(Action::CampaignTargetDarkestSecret),
        140 => Some(Action::CampaignTargetPawn),
        141..=150 => Some(Action::CampaignUseBattlePlan((id - 141) as u8)),
        151..=154 => OathGoal::from_u8((id - 151) as u8).map(Action::VowOath),
        155 => Some(Action::DealOfferFavorPlus),
        156 => Some(Action::DealOfferFavorMinus),
        157 => Some(Action::DealOfferSecretPlus),
        158 => Some(Action::DealOfferSecretMinus),
        159 => Some(Action::DealRequestFavorPlus),
        160 => Some(Action::DealRequestFavorMinus),
        161 => Some(Action::DealRequestSecretPlus),
        162 => Some(Action::DealRequestSecretMinus),
        163..=165 => Some(Action::DealToggleOfferRelic((id - 163) as u8)),
        166..=168 => Some(Action::DealToggleRequestRelic((id - 166) as u8)),
        169..=171 => Some(Action::DealToggleOfferAdviser((id - 169) as u8)),
        172..=174 => Some(Action::DealToggleRequestAdviser((id - 172) as u8)),
        175..=178 => Some(Action::DealSelectReliquary((id - 175) as u8)),
        179 => Some(Action::DealToggleAllowPeek),
        180 => Some(Action::DealCounterOffer),
        181 => Some(Action::DealAddNonAggression),
        182 => Some(Action::DealAddMustCampaignLeader),
        183 => Some(Action::DealToggleContractPenalty),
        184 => Some(Action::DealToggleOfferSite),
        185 => Some(Action::DealToggleRequestSite),
        186..=190 => Some(Action::TalkProposeAlliance((id - 186 + 1) as u8)),
        191..=195 => Some(Action::TalkRequestAttack((id - 191 + 1) as u8)),
        196..=200 => Some(Action::TalkPledgeNonAggression((id - 196 + 1) as u8)),
        201 => Some(Action::TalkRequestCitizenship),
        202 => Some(Action::TalkAskForDeal),
        203 => Some(Action::TalkAcceptVerbal),
        204 => Some(Action::TalkRejectVerbal),
        205..=210 => Suit::from_u8((id - 205) as u8).map(Action::TalkClaimSuit),
        211..=213 => Some(Action::TalkShowAdviser((id - 211) as u8)),
        214 => Some(Action::PassTalk),
        215 => Some(Action::ChronicleSkip),
        _ => None,
    }
}

pub fn encode_action(action: Action) -> ActionId {
    match action {
        Action::Travel(s) => s as u16,
        Action::SearchDeck => 8,
        Action::SearchDiscard => 9,
        Action::Muster(s) => 10 + s as u16,
        Action::TradeFavor(s) => 13 + s as u16,
        Action::TradeSecrets(s) => 16 + s as u16,
        Action::RecoverRelic(s) => 19 + s as u16,
        Action::RecoverPeoplesFavor => 22,
        Action::RecoverDarkestSecret => 23,
        Action::CampaignDeclare(r) => 24 + (r - 1) as u16,
        Action::CampaignDeclareBandits => 29,
        Action::FlipAdviser(s) => 30 + s as u16,
        Action::DiscardAdviser(s) => 33 + s as u16,
        Action::UseCardAction(s) => 36 + s as u16,
        Action::PeekSiteRelic(s) => 47 + s as u16,
        Action::PeekReliquary => 50,
        Action::MoveWarbandsToBoard => 51,
        Action::MoveWarbandsToSite => 52,
        Action::OfferCitizenship(r) => 53 + (r - 1) as u16,
        Action::ExileCitizen(r) => 58 + (r - 1) as u16,
        Action::SelfExile => 63,
        Action::EndActPhase => 64,
        Action::SelectSite(s) => 65 + s as u16,
        Action::SelectSlot(s) => 73 + s as u16,
        Action::SelectRelPlayer(r) => 77 + r as u16,
        Action::SelectSuit(s) => 83 + s as u16,
        Action::SelectAmount(a) => 89 + a as u16,
        Action::Confirm => 100,
        Action::Decline => 101,
        Action::SearchPlay { card_idx, dest } => 102 + (card_idx as u16) * 4 + dest as u16,
        Action::SearchDiscardCard(c) => 126 + c as u16,
        Action::CampaignTargetRelic(r) => 132 + r as u16,
        Action::CampaignTargetPeoplesFavor => 138,
        Action::CampaignTargetDarkestSecret => 139,
        Action::CampaignTargetPawn => 140,
        Action::CampaignUseBattlePlan(s) => 141 + s as u16,
        Action::VowOath(g) => 151 + g as u16,
        Action::DealOfferFavorPlus => 155,
        Action::DealOfferFavorMinus => 156,
        Action::DealOfferSecretPlus => 157,
        Action::DealOfferSecretMinus => 158,
        Action::DealRequestFavorPlus => 159,
        Action::DealRequestFavorMinus => 160,
        Action::DealRequestSecretPlus => 161,
        Action::DealRequestSecretMinus => 162,
        Action::DealToggleOfferRelic(i) => 163 + i as u16,
        Action::DealToggleRequestRelic(i) => 166 + i as u16,
        Action::DealToggleOfferAdviser(i) => 169 + i as u16,
        Action::DealToggleRequestAdviser(i) => 172 + i as u16,
        Action::DealSelectReliquary(i) => 175 + i as u16,
        Action::DealToggleAllowPeek => 179,
        Action::DealCounterOffer => 180,
        Action::DealAddNonAggression => 181,
        Action::DealAddMustCampaignLeader => 182,
        Action::DealToggleContractPenalty => 183,
        Action::DealToggleOfferSite => 184,
        Action::DealToggleRequestSite => 185,
        Action::TalkProposeAlliance(r) => 186 + (r - 1) as u16,
        Action::TalkRequestAttack(r) => 191 + (r - 1) as u16,
        Action::TalkPledgeNonAggression(r) => 196 + (r - 1) as u16,
        Action::TalkRequestCitizenship => 201,
        Action::TalkAskForDeal => 202,
        Action::TalkAcceptVerbal => 203,
        Action::TalkRejectVerbal => 204,
        Action::TalkClaimSuit(s) => 205 + s as u16,
        Action::TalkShowAdviser(s) => 211 + s as u16,
        Action::PassTalk => 214,
        Action::ChronicleSkip => 215,
    }
}

#[inline]
pub fn resolve_rel_player(acting: PlayerId, rel: u8, num_players: u8) -> PlayerId {
    ((acting as usize + rel as usize) % num_players as usize) as PlayerId
}

/// Human-readable description for UI and action logs.
pub fn describe_action(gs: &GameState, id: ActionId) -> String {
    let acting = gs.decision.acting_player().unwrap_or(gs.current_player);
    let p = &gs.players[acting as usize];
    let site = &gs.sites[p.pawn_site as usize];
    let Some(act) = decode_action(id) else {
        return format!("Unknown action {id}");
    };
    match act {
        Action::Travel(si) => {
            let s = &gs.sites[si as usize];
            if s.is_faceup {
                format!("Travel to {} (site {})", get_card(s.site_id).name, si)
            } else {
                format!("Travel to facedown site {} ({})", si, s.region.name())
            }
        }
        Action::SearchDeck => "Search the World Deck".into(),
        Action::SearchDiscard => format!("Search {} Discard Pile", site.region.name()),
        Action::Muster(slot) => {
            let cid = site.cards[slot as usize];
            format!("Muster on {} [slot {}]", get_card(cid).name, slot)
        }
        Action::TradeFavor(slot) => {
            let cid = site.cards[slot as usize];
            format!("Trade for Favor with {} [slot {}]", get_card(cid).name, slot)
        }
        Action::TradeSecrets(slot) => {
            let cid = site.cards[slot as usize];
            format!("Trade for Secrets with {} [slot {}]", get_card(cid).name, slot)
        }
        Action::RecoverRelic(slot) => format!("Recover Relic [slot {}]", slot),
        Action::RecoverPeoplesFavor => "Recover the People's Favor".into(),
        Action::RecoverDarkestSecret => "Recover the Darkest Secret".into(),
        Action::CampaignDeclare(rel) => {
            let tgt = resolve_rel_player(acting, rel, gs.num_players);
            format!("Campaign against Player {}", tgt)
        }
        Action::CampaignDeclareBandits => "Campaign against Bandits".into(),
        Action::FlipAdviser(slot) => {
            let cid = p.advisers[slot as usize];
            format!("Flip Adviser {} faceup", get_card(cid).name)
        }
        Action::DiscardAdviser(slot) => {
            let cid = p.advisers[slot as usize];
            format!("Discard Adviser {}", get_card(cid).name)
        }
        Action::UseCardAction(idx) => match idx {
            0..=2 => format!("Use Action: {}", get_card(site.cards[idx as usize]).name),
            3..=5 => format!("Use Adviser Action: {}", get_card(p.advisers[(idx - 3) as usize]).name),
            6 => format!("Use Site Action: {}", get_card(site.site_id).name),
            7..=10 => {
                let r_idx = (idx - 7) as usize;
                let name = p.relics.get(r_idx).map(|&c| get_card(c).name).unwrap_or("Relic");
                format!("Use Relic Action: {}", name)
            }
            _ => "Use Card Action".into(),
        },
        Action::PeekSiteRelic(slot) => format!("Peek at Relic [slot {}]", slot),
        Action::PeekReliquary => "Peek in Imperial Reliquary".into(),
        Action::MoveWarbandsToBoard => "Move Warbands from Site to Board".into(),
        Action::MoveWarbandsToSite => "Move Warbands from Board to Site".into(),
        Action::OfferCitizenship(rel) => {
            let tgt = resolve_rel_player(acting, rel, gs.num_players);
            format!("Offer Citizenship to Player {}", tgt)
        }
        Action::ExileCitizen(rel) => {
            let tgt = resolve_rel_player(acting, rel, gs.num_players);
            format!("Exile Citizen Player {}", tgt)
        }
        Action::SelfExile => "Self-Exile (become Exile)".into(),
        Action::EndActPhase => "End Act Phase".into(),
        Action::SelectSite(si) => {
            let s = &gs.sites[si as usize];
            if s.is_faceup {
                format!("Select {} (site {})", get_card(s.site_id).name, si)
            } else {
                format!("Select site {} ({})", si, s.region.name())
            }
        }
        Action::SelectSlot(s) => format!("Select Slot {}", s),
        Action::SelectRelPlayer(r) => {
            let tgt = resolve_rel_player(acting, r, gs.num_players);
            format!("Select Player {}", tgt)
        }
        Action::SelectSuit(s) => format!("Select {} Suit", s.name()),
        Action::SelectAmount(a) => format!("Choose {}", a),
        Action::Confirm => "Confirm / Accept".into(),
        Action::Decline => "Decline / Skip".into(),
        Action::SearchPlay { card_idx, dest } => {
            let name = gs
                .search
                .as_ref()
                .and_then(|s| s.drawn_cards.get(card_idx as usize))
                .map(|&c| get_card(c).name)
                .unwrap_or("Card");
            let d = match dest {
                0 => "to Site",
                1 => "as Faceup Adviser",
                2 => "as Facedown Adviser",
                _ => "as Revealed Vision",
            };
            format!("Play {} {}", name, d)
        }
        Action::SearchDiscardCard(idx) => {
            let name = gs
                .search
                .as_ref()
                .and_then(|s| s.drawn_cards.get(idx as usize))
                .map(|&c| get_card(c).name)
                .unwrap_or("Card");
            format!("Discard {}", name)
        }
        Action::CampaignTargetRelic(slot) => format!("Target Relic [slot {}]", slot),
        Action::CampaignTargetPeoplesFavor => "Target People's Favor".into(),
        Action::CampaignTargetDarkestSecret => "Target Darkest Secret".into(),
        Action::CampaignTargetPawn => "Target Pawn & Favor".into(),
        Action::CampaignUseBattlePlan(slot) => format!("Use Battle Plan [slot {}]", slot),
        Action::VowOath(g) => format!("Vow Oath of {:?}", g),
        Action::DealOfferFavorPlus => "Offer +1 Favor".into(),
        Action::DealOfferFavorMinus => "Offer -1 Favor".into(),
        Action::DealOfferSecretPlus => "Offer +1 Secret".into(),
        Action::DealOfferSecretMinus => "Offer -1 Secret".into(),
        Action::DealRequestFavorPlus => "Request +1 Favor".into(),
        Action::DealRequestFavorMinus => "Request -1 Favor".into(),
        Action::DealRequestSecretPlus => "Request +1 Secret".into(),
        Action::DealRequestSecretMinus => "Request -1 Secret".into(),
        Action::DealToggleOfferRelic(i) => format!("Toggle Offer Relic {}", i),
        Action::DealToggleRequestRelic(i) => format!("Toggle Request Relic {}", i),
        Action::DealToggleOfferAdviser(i) => format!("Toggle Offer Adviser {}", i),
        Action::DealToggleRequestAdviser(i) => format!("Toggle Request Adviser {}", i),
        Action::DealSelectReliquary(i) => format!("Offer Reliquary Relic {}", i),
        Action::DealToggleAllowPeek => "Toggle Allow Reliquary Peek".into(),
        Action::DealCounterOffer => "Counter-Offer".into(),
        Action::DealAddNonAggression => "Add Non-Aggression Contract".into(),
        Action::DealAddMustCampaignLeader => "Add Must-Campaign-Leader Contract".into(),
        Action::DealToggleContractPenalty => "Toggle Hard Enforcement vs Breach Penalty".into(),
        Action::DealToggleOfferSite => "Toggle Offer Ruled Site".into(),
        Action::DealToggleRequestSite => "Toggle Request Ruled Site".into(),
        Action::TalkProposeAlliance(r) => {
            format!("Talk: Propose alliance with P{}", resolve_rel_player(acting, r, gs.num_players))
        }
        Action::TalkRequestAttack(r) => {
            format!("Talk: Ask table to attack P{}", resolve_rel_player(acting, r, gs.num_players))
        }
        Action::TalkPledgeNonAggression(r) => {
            format!("Talk: Pledge non-aggression to P{}", resolve_rel_player(acting, r, gs.num_players))
        }
        Action::TalkRequestCitizenship => "Talk: Request Citizenship".into(),
        Action::TalkAskForDeal => "Talk: Ask to negotiate a deal".into(),
        Action::TalkAcceptVerbal => "Talk: Agree verbally".into(),
        Action::TalkRejectVerbal => "Talk: Refuse verbally".into(),
        Action::TalkClaimSuit(s) => format!("Talk: Claim {} adviser", s.name()),
        Action::TalkShowAdviser(s) => format!("Show Facedown Adviser [slot {}]", s),
        Action::PassTalk => "Pass (no message)".into(),
        Action::ChronicleSkip => "Skip Chronicle option".into(),
    }
}

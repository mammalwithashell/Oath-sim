use serde::{Deserialize, Serialize};
use smallvec::SmallVec;
use std::collections::VecDeque;

use crate::cards::get_card;
use crate::rng::FastRng;
use crate::types::*;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SiteState {
    pub site_id: CardId,
    pub region: Region,
    pub is_faceup: bool,
    pub capacity: u8,
    pub cards: [CardId; MAX_CARDS_PER_SITE],
    pub card_favor: [u8; MAX_CARDS_PER_SITE],
    pub card_secrets: [u8; MAX_CARDS_PER_SITE],
    pub relics: SmallVec<[CardId; 4]>,
    pub ruling_player: Option<PlayerId>,
    pub warbands: u8,
    pub warband_color: Option<PlayerId>, // 0 = Imperial purple, 1..5 = Exile color
    pub site_favor: u8,
    pub site_secrets: u8,
    /// Bitmask of suits discarded at this site this turn (for Homeland/Search site powers)
    pub suits_discarded_this_turn: u8,
}

impl SiteState {
    pub fn empty(site_id: CardId, region: Region) -> Self {
        let def = get_card(site_id);
        Self {
            site_id,
            region,
            is_faceup: false,
            capacity: def.capacity,
            cards: [CARD_EMPTY; MAX_CARDS_PER_SITE],
            card_favor: [0; MAX_CARDS_PER_SITE],
            card_secrets: [0; MAX_CARDS_PER_SITE],
            relics: SmallVec::new(),
            ruling_player: None,
            warbands: 0,
            warband_color: None,
            site_favor: 0,
            site_secrets: 0,
            suits_discarded_this_turn: 0,
        }
    }

    pub fn num_cards(&self) -> usize {
        self.cards[..self.capacity as usize]
            .iter()
            .filter(|&&c| c != CARD_EMPTY)
            .count()
    }

    pub fn first_empty_slot(&self) -> Option<usize> {
        self.cards[..self.capacity as usize]
            .iter()
            .position(|&c| c == CARD_EMPTY)
    }

    pub fn has_empty_slot(&self) -> bool {
        self.first_empty_slot().is_some()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PlayerState {
    pub role: Role,
    pub pawn_site: SiteIndex,
    pub supply: u8,
    pub warbands_board: u8,
    pub warbands_bank: u8,
    pub favor: u8,
    pub secrets_faceup: u8,
    pub secrets_facedown: u8,
    pub advisers: [CardId; MAX_ADVISERS],
    pub adviser_faceup: [bool; MAX_ADVISERS],
    pub relics: SmallVec<[CardId; 6]>,
    pub revealed_vision: Option<CardId>,
    pub color: PlayerId,
    pub talk_remaining: u8,
}

impl PlayerState {
    pub fn new(role: Role, color: PlayerId) -> Self {
        Self {
            role,
            pawn_site: 0,
            supply: 7,
            warbands_board: 0,
            warbands_bank: if role == Role::Chancellor {
                MAX_WARBANDS_CHANCELLOR
            } else {
                MAX_WARBANDS_EXILE
            },
            favor: if role == Role::Chancellor { 2 } else { 1 },
            secrets_faceup: 1,
            secrets_facedown: 0,
            advisers: [CARD_EMPTY; MAX_ADVISERS],
            adviser_faceup: [false; MAX_ADVISERS],
            relics: SmallVec::new(),
            revealed_vision: None,
            color,
            talk_remaining: MAX_TALK_PER_TURN,
        }
    }

    #[inline]
    pub fn total_secrets(&self) -> u8 {
        self.secrets_faceup + self.secrets_facedown
    }

    pub fn first_empty_adviser(&self) -> Option<usize> {
        self.advisers.iter().position(|&c| c == CARD_EMPTY)
    }

    pub fn num_advisers(&self) -> usize {
        self.advisers.iter().filter(|&&c| c != CARD_EMPTY).count()
    }

    pub fn has_relic(&self, relic_id: CardId) -> bool {
        self.relics.contains(&relic_id)
    }

    pub fn faceup_adviser_suit_count(&self, suit: Suit) -> u8 {
        let mut count = 0;
        for i in 0..MAX_ADVISERS {
            if self.advisers[i] != CARD_EMPTY && self.adviser_faceup[i] {
                if get_card(self.advisers[i]).suit == Some(suit) {
                    count += if self.advisers[i] == 148 && suit == Suit::Hearth {
                        2
                    } else {
                        1
                    };
                }
            }
        }
        count
    }

    pub fn has_faceup_adviser_suit(&self, suit: Suit) -> bool {
        self.faceup_adviser_suit_count(suit) > 0
    }
}

/// Per-player imperfect information tracking for exact observations and IS-MCTS determinization.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct KnowledgeState {
    /// Known facedown advisers of other players: bit (player * 3 + slot)
    pub known_advisers_mask: u32,
    /// Known Reliquary slots: bit (slot 0..4)
    pub known_reliquary_mask: u8,
    /// Known facedown site relics: (site_idx, relic_slot) bitmask (8 * 4 = 32 bits)
    pub known_site_relics_mask: u32,
    /// Known facedown sites (via Ivory Eye): bit (site_idx 0..8)
    pub known_facedown_sites_mask: u8,
    /// Top N world deck cards peeked (e.g. Oracular Pig)
    pub known_world_deck_top: SmallVec<[CardId; 4]>,
}

impl KnowledgeState {
    pub fn knows_adviser(&self, owner: PlayerId, slot: usize) -> bool {
        let bit = (owner as usize) * MAX_ADVISERS + slot;
        (self.known_advisers_mask & (1u32 << bit)) != 0
    }

    pub fn mark_adviser_known(&mut self, owner: PlayerId, slot: usize) {
        let bit = (owner as usize) * MAX_ADVISERS + slot;
        self.known_advisers_mask |= 1u32 << bit;
    }

    pub fn clear_adviser_known(&mut self, owner: PlayerId, slot: usize) {
        let bit = (owner as usize) * MAX_ADVISERS + slot;
        self.known_advisers_mask &= !(1u32 << bit);
    }

    pub fn knows_reliquary(&self, slot: usize) -> bool {
        (self.known_reliquary_mask & (1u8 << slot)) != 0
    }

    pub fn mark_reliquary_known(&mut self, slot: usize) {
        self.known_reliquary_mask |= 1u8 << slot;
    }

    pub fn knows_site_relic(&self, site: SiteIndex, slot: usize) -> bool {
        if slot >= 4 {
            return false;
        }
        let bit = (site as usize) * 4 + slot;
        (self.known_site_relics_mask & (1u32 << bit)) != 0
    }

    pub fn mark_site_relic_known(&mut self, site: SiteIndex, slot: usize) {
        if slot < 4 {
            let bit = (site as usize) * 4 + slot;
            self.known_site_relics_mask |= 1u32 << bit;
        }
    }
}

// ── Search State ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SearchState {
    pub player: PlayerId,
    pub from_deck: bool,
    pub discard_region: Region,
    pub drawn_cards: SmallVec<[CardId; 6]>,
    pub remaining: SmallVec<[bool; 6]>,
    pub played_one: bool,
    pub reveal_all: bool, // Truthful Harp
}

// ── Campaign State ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CampaignTarget {
    Site(SiteIndex),
    Relic(CardId),
    Banner(Banner),
    Pawn,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CampaignState {
    pub attacker: PlayerId,
    /// None = Bandits
    pub defender: Option<PlayerId>,
    pub targets: SmallVec<[CampaignTarget; 12]>,
    pub target_sites: SmallVec<[SiteIndex; 8]>,
    pub allies: SmallVec<[PlayerId; 5]>,
    pub attack_dice: i8,
    pub defense_dice: i8,
    pub attack_swords: i16,
    pub defense_shields: i16,
    pub attacker_warbands_killed: u8,
    pub defender_warbands_killed: u8,
    pub used_battle_plans: SmallVec<[CardId; 12]>,
    pub active_bp_cards_attacker: SmallVec<[CardId; 8]>,
    pub active_bp_cards_defender: SmallVec<[CardId; 8]>,
    pub remaining_sites_to_place: SmallVec<[SiteIndex; 8]>,
    pub banish_destination: Option<SiteIndex>,
    pub attacker_won: Option<bool>,
    pub attacker_bp_done: bool,
    pub defender_bp_done: bool,
    pub force_sacrifice_bonus: i16,
}

impl CampaignState {
    pub fn new(attacker: PlayerId, defender: Option<PlayerId>) -> Self {
        Self {
            attacker,
            defender,
            targets: SmallVec::new(),
            target_sites: SmallVec::new(),
            allies: SmallVec::new(),
            attack_dice: 0,
            defense_dice: 0,
            attack_swords: 0,
            defense_shields: 0,
            attacker_warbands_killed: 0,
            defender_warbands_killed: 0,
            used_battle_plans: SmallVec::new(),
            active_bp_cards_attacker: SmallVec::new(),
            active_bp_cards_defender: SmallVec::new(),
            remaining_sites_to_place: SmallVec::new(),
            banish_destination: None,
            attacker_won: None,
            attacker_bp_done: false,
            defender_bp_done: false,
            force_sacrifice_bonus: 0,
        }
    }
}

// ── Binding Deals & Tribunal Contracts ────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DealKind {
    Citizenship,       // §6.6: Reliquary relic (mandatory) + favor, secrets, relics, banners, warbands
    TinkersFair,       // OATH-013: favor, secrets, relics
    TheGathering,      // OATH-027: favor, secrets, relics, advisers
    DeedWriter,        // OATH-146: favor, secrets, ruled sites
    FestivalDistrict,  // OATH-205: favor, secrets, advisers
    TheTribunal,       // OATH-245: favor, secrets + binding future contracts
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct DealBundle {
    pub favor: u8,
    pub secrets: u8,
    pub relics: SmallVec<[CardId; 4]>,
    pub advisers: SmallVec<[u8; 3]>,    // adviser slots 0..3
    pub sites: SmallVec<[SiteIndex; 4]>,
    pub banners: SmallVec<[Banner; 2]>,
    pub reliquary_slot: Option<u8>,
    pub warbands: u8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractClause {
    NonAggression {
        actor: PlayerId,
        target: PlayerId,
        until_round: u8,
    },
    SiteHandsOff {
        actor: PlayerId,
        site: SiteIndex,
        until_round: u8,
    },
    MustCampaign {
        actor: PlayerId,
        target: PlayerId,
        by_round: u8,
    },
    MustNotRecoverBanner {
        actor: PlayerId,
        banner: Banner,
        until_round: u8,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EnforcementMode {
    HardEnforced,
    PenaltyOnBreach { favor: u8, secrets: u8 },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TribunalContract {
    pub party_a: PlayerId,
    pub party_b: PlayerId,
    pub clause: ContractClause,
    pub enforcement: EnforcementMode,
    pub fulfilled: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DealState {
    pub kind: DealKind,
    pub initiator: PlayerId,
    pub proposer: PlayerId,
    pub responder: PlayerId,
    pub round: u8, // 0..MAX_DEAL_ROUNDS
    pub edits: u8, // bounded edits per compose round to prevent infinite toggle loops
    pub offer: DealBundle,
    pub request: DealBundle,
    pub contracts: SmallVec<[TribunalContract; 2]>,
    pub allow_reliquary_peek: bool,
}

// ── Table Talk ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum TalkIntent {
    ProposeAlliance = 0,
    RequestAttack = 1,
    PledgeNonAggression = 2,
    RequestCitizenship = 3,
    ThreatenExile = 4,
    AskForDeal = 5,
    AcceptVerbal = 6,
    RejectVerbal = 7,
    ClaimSuit = 8,
    ShowedAdviser = 9,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct TalkEvent {
    pub round: u8,
    pub sender: PlayerId,
    pub target: Option<PlayerId>,
    pub intent: TalkIntent,
    pub suit: Option<Suit>,
    pub shown_card: Option<CardId>,
}

// ── DecisionPoint & PendingEffect Stack ───────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DecisionPoint {
    /// Normal Act Phase for `player`
    TurnAct { player: PlayerId },
    /// Search: play or discard drawn cards
    SearchResolve { player: PlayerId },
    /// Choose a site (e.g., banish destination, card power target, Brass Horse)
    ChooseSite {
        player: PlayerId,
        reason: ChoiceReason,
        allowed_mask: u8, // bitmask of SiteIndex 0..8
    },
    /// Choose a card slot at a site (e.g., Great Slum discard, Horned Mask swap)
    ChooseSiteCard {
        player: PlayerId,
        site: SiteIndex,
        reason: ChoiceReason,
        allowed_slots: u8, // bitmask 0..3
    },
    /// Choose an adviser slot (e.g., replace 4th adviser, Horned Mask swap)
    ChooseAdviser {
        player: PlayerId,
        owner: PlayerId,
        reason: ChoiceReason,
        allowed_slots: u8,
    },
    /// Choose a favor bank suit (e.g., People's Favor wake tie, Alchemist, Memory of Nature)
    ChooseSuit {
        player: PlayerId,
        reason: ChoiceReason,
        allowed_mask: u8, // bitmask of Suit 0..6
    },
    /// Choose a player (e.g., deal partner, Whistle target, Conspiracy target)
    ChoosePlayer {
        player: PlayerId,
        reason: ChoiceReason,
        allowed_mask: u8, // bitmask of PlayerId 0..6
    },
    /// Choose an amount in [min, max]
    ChooseAmount {
        player: PlayerId,
        reason: ChoiceReason,
        min: u8,
        max: u8,
    },
    /// Yes/No optional trigger or confirmation
    ChooseYesNo {
        player: PlayerId,
        reason: ChoiceReason,
        source_card: CardId,
    },
    /// Campaign: attacker selects targets
    CampaignTargets { player: PlayerId },
    /// Campaign: attacker or defender/ally selects battle plans
    CampaignBattlePlan {
        player: PlayerId,
        is_attacker: bool,
    },
    /// Campaign: attacker chooses whether to sacrifice warbands to win
    CampaignSacrifice {
        player: PlayerId,
        min_needed: u8,
        max_available: u8,
    },
    /// Campaign: attacker places warbands on captured site
    CampaignPlaceWarbands {
        player: PlayerId,
        site: SiteIndex,
        max_warbands: u8,
    },
    /// Campaign: attacker chooses whether to burn banished defender's favor
    CampaignBanishBurn {
        player: PlayerId,
        defender: PlayerId,
    },
    /// Binding Deal: proposer builds offer/request bundle (and optional Tribunal contracts)
    DealCompose { player: PlayerId },
    /// Binding Deal: responder accepts, declines, or counters
    DealRespond { player: PlayerId },
    /// Reactive 1-message table talk window before a high-stakes response
    ReactiveTalk {
        player: PlayerId,
        context: ReactiveContext,
    },
    /// Post-game Chronicle: winner vows next Oath
    ChronicleVow { player: PlayerId },
    /// Post-game Chronicle: winner optionally builds/repairs edifice at ruled site
    ChronicleEdifice { player: PlayerId, site: SiteIndex },
    /// Game has ended
    Terminal,
}

impl DecisionPoint {
    pub fn acting_player(&self) -> Option<PlayerId> {
        match *self {
            DecisionPoint::TurnAct { player }
            | DecisionPoint::SearchResolve { player }
            | DecisionPoint::ChooseSite { player, .. }
            | DecisionPoint::ChooseSiteCard { player, .. }
            | DecisionPoint::ChooseAdviser { player, .. }
            | DecisionPoint::ChooseSuit { player, .. }
            | DecisionPoint::ChoosePlayer { player, .. }
            | DecisionPoint::ChooseAmount { player, .. }
            | DecisionPoint::ChooseYesNo { player, .. }
            | DecisionPoint::CampaignTargets { player }
            | DecisionPoint::CampaignBattlePlan { player, .. }
            | DecisionPoint::CampaignSacrifice { player, .. }
            | DecisionPoint::CampaignPlaceWarbands { player, .. }
            | DecisionPoint::CampaignBanishBurn { player, .. }
            | DecisionPoint::DealCompose { player }
            | DecisionPoint::DealRespond { player }
            | DecisionPoint::ReactiveTalk { player, .. }
            | DecisionPoint::ChronicleVow { player }
            | DecisionPoint::ChronicleEdifice { player, .. } => Some(player),
            DecisionPoint::Terminal => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum ReactiveContext {
    CampaignDefense = 0,
    DealResponse = 1,
    CitizenshipOffer = 2,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum ChoiceReason {
    PeoplesFavorWake = 0,
    SiteWakeResource = 1,
    ReplaceAdviser = 2,
    DiscardSiteCard = 3,
    BanishDestination = 4,
    MoveWarbandsToBoard = 5,
    MoveWarbandsToSite = 6,
    CardGainFavorBank = 7,
    CardTargetPlayer = 8,
    CardTargetSite = 9,
    CardTargetSiteCard = 10,
    CardTargetAdviser = 11,
    CardYesNo = 12,
    DealPartner = 13,
    ImperialAllyJoin = 14,
    ChronicleBuildEdifice = 15,
    SqualidDistrictRoll = 16,
    DowsingSticksKeep = 17,
    BuriedGiantTravel = 18,
    ConspiracyTarget = 19,
}

/// Continuation frame pushed onto `GameState.effect_stack` whenever an effect or rule
/// pauses for player input.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PendingEffect {
    ResumeWakePhase { player: PlayerId, step: u8 },
    ResumeRestPhase { player: PlayerId },
    ResumeSearchPlay {
        player: PlayerId,
        card_id: CardId,
        dest: u8, // 0=site, 1=adviser_up, 2=adviser_down
    },
    ResumeCampaignAfterReactiveTalk,
    ResumeCampaignAfterDefenderBp,
    ResumeCampaignBanish { defender: PlayerId },
    ResumeDealAfterReactiveTalk,
    ResumeCardEffect {
        card_id: CardId,
        player: PlayerId,
        step: u8,
        aux: u16,
    },
    ResumeEndOfRoundCheck { roll: u8 },
}

// ── Chronicle State ───────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChronicleSiteSnapshot {
    pub site_id: CardId,
    pub cards: SmallVec<[CardId; 3]>,
    pub relics: SmallVec<[CardId; 3]>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChronicleState {
    pub archive: [Vec<CardId>; NUM_SUITS],
    pub dispossessed: Vec<CardId>,
    pub chronicled_sites: Vec<ChronicleSiteSnapshot>,
    pub site_deck: Vec<CardId>,
    pub relic_deck: Vec<CardId>,
    pub world_deck: Vec<CardId>,
    pub oath_goal: OathGoal,
    pub player_boards: Vec<Role>,
    pub last_winner: Option<PlayerId>,
    pub games_played: u32,
}

// ── Core GameState ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameState {
    pub players: [PlayerState; MAX_PLAYERS],
    pub num_players: u8,
    pub current_player: PlayerId,
    pub turn_order: [PlayerId; MAX_PLAYERS],

    pub sites: [SiteState; MAX_SITES],

    pub world_deck: Vec<CardId>,
    pub discard_piles: [Vec<CardId>; NUM_REGIONS],
    pub relic_deck: Vec<CardId>,
    pub dispossessed: Vec<CardId>,
    pub archive: [Vec<CardId>; NUM_SUITS],
    pub site_deck: Vec<CardId>,
    pub reliquary: SmallVec<[CardId; 4]>,

    pub favor_banks: [u8; NUM_SUITS],
    pub shared_secrets: u8,

    pub peoples_favor_holder: Option<PlayerId>,
    pub peoples_favor_tokens: u8,
    pub peoples_favor_is_mob: bool,
    pub darkest_secret_holder: Option<PlayerId>,
    pub darkest_secret_tokens: u8,

    pub oathkeeper_holder: Option<PlayerId>,
    pub oathkeeper_side: TitleSide,
    pub oath_goal: OathGoal,
    pub successor_goal: SuccessorGoal,

    pub round_number: u8,
    pub visions_drawn: u8,
    pub turn_in_round: u8,
    pub phase: Phase,

    pub decision: DecisionPoint,
    pub effect_stack: Vec<PendingEffect>,

    pub search: Option<SearchState>,
    pub campaign: Option<CampaignState>,
    pub deal: Option<DealState>,
    pub active_contracts: SmallVec<[TribunalContract; 6]>,
    pub talk_log: VecDeque<TalkEvent>,
    pub knowledge: [KnowledgeState; MAX_PLAYERS],

    pub obsidian_cage_warbands: [u8; MAX_PLAYERS],
    pub scepter_taken_this_turn: bool,
    pub used_card_powers_this_turn: SmallVec<[CardId; 16]>,
    pub supply_spent_this_turn: u8,
    pub actions_taken_this_turn: u16,

    pub is_game_over: bool,
    pub winner: Option<PlayerId>,
    pub win_type: Option<WinType>,
    pub vowed_oath: Option<OathGoal>,
    pub chronicle_enabled: bool,

    pub rng: FastRng,
    pub step_count: u32,
}

impl GameState {
    #[inline]
    pub fn chancellor_index(&self) -> PlayerId {
        for i in 0..self.num_players {
            if self.players[i as usize].role == Role::Chancellor {
                return i;
            }
        }
        0
    }

    #[inline]
    pub fn is_imperial(&self, player: PlayerId) -> bool {
        self.players[player as usize].role.is_imperial()
    }

    /// True if `player` rules `site_idx` (including Imperial sharing and Bandit Crown OATH-221).
    pub fn player_rules_site(&self, player: PlayerId, site_idx: SiteIndex) -> bool {
        let s = &self.sites[site_idx as usize];
        if !s.is_faceup {
            return false;
        }
        if s.ruling_player == Some(player) {
            return true;
        }
        if self.is_imperial(player)
            && s.warband_color == Some(0)
            && s.warbands > 0
            && s.ruling_player.map(|r| self.is_imperial(r)).unwrap_or(false)
        {
            return true;
        }
        // Bandit Crown (OATH-221): holder rules empty sites
        if s.ruling_player.is_none()
            && self.players[player as usize].has_relic(RELIC_BANDIT_CROWN)
        {
            return true;
        }
        false
    }

    pub fn count_sites_ruled(&self, player: PlayerId) -> u8 {
        (0..MAX_SITES as u8)
            .filter(|&i| self.player_rules_site(player, i))
            .count() as u8
    }

    pub fn count_relics_and_banners(&self, player: PlayerId) -> u8 {
        let mut n = self.players[player as usize].relics.len() as u8;
        if self.peoples_favor_holder == Some(player) {
            n += 1;
        }
        if self.darkest_secret_holder == Some(player) {
            n += 1;
        }
        n
    }

    pub fn player_has_card_access(&self, player: PlayerId, card_id: CardId) -> bool {
        let p = &self.players[player as usize];
        if p.relics.contains(&card_id) {
            return true;
        }
        for i in 0..MAX_ADVISERS {
            if p.advisers[i] == card_id && p.adviser_faceup[i] {
                return true;
            }
        }
        // Cards at pawn's site or any site ruled by player
        for si in 0..MAX_SITES as u8 {
            let s = &self.sites[si as usize];
            if !s.is_faceup {
                continue;
            }
            if p.pawn_site == si || self.player_rules_site(player, si) {
                if s.cards[..s.capacity as usize].contains(&card_id) {
                    return true;
                }
            }
            // Grand Mask (OATH-215): Exile rules cards at Imperial sites during their turn
            if p.role == Role::Exile
                && self.current_player == player
                && p.has_relic(RELIC_GRAND_MASK)
                && s.warband_color == Some(0)
                && s.warbands > 0
                && s.cards[..s.capacity as usize].contains(&card_id)
            {
                return true;
            }
        }
        false
    }

    /// Determinize hidden information from `observer`'s point of view for AlphaZero / IS-MCTS.
    /// Keeps all public info and everything in `self.knowledge[observer]` fixed, while
    /// resampling unseen hidden cards uniformly without replacement.
    pub fn determinize(&self, observer: PlayerId, rng: &mut FastRng) -> GameState {
        let mut cloned = self.clone();
        cloned.rng = *rng;
        let kb = &self.knowledge[observer as usize];

        // 1. Collect all unseen denizen/vision cards:
        //    - world_deck (except known top cards)
        //    - other players' unknown facedown advisers
        let known_top_len = kb.known_world_deck_top.len().min(cloned.world_deck.len());
        let mut hidden_deck_pool: Vec<CardId> = Vec::new();
        let mut adviser_slots: Vec<(usize, usize)> = Vec::new();

        // Bottom part of world_deck (index 0..len - known_top_len; top is end of Vec)
        let unknown_deck_len = cloned.world_deck.len().saturating_sub(known_top_len);
        hidden_deck_pool.extend_from_slice(&cloned.world_deck[..unknown_deck_len]);

        for pi in 0..cloned.num_players as usize {
            if pi == observer as usize {
                continue;
            }
            for slot in 0..MAX_ADVISERS {
                let cid = cloned.players[pi].advisers[slot];
                if cid != CARD_EMPTY
                    && !cloned.players[pi].adviser_faceup[slot]
                    && !kb.knows_adviser(pi as PlayerId, slot)
                {
                    hidden_deck_pool.push(cid);
                    adviser_slots.push((pi, slot));
                }
            }
        }
        rng.shuffle(&mut hidden_deck_pool);
        let mut cursor = 0;
        for i in 0..unknown_deck_len {
            cloned.world_deck[i] = hidden_deck_pool[cursor];
            cursor += 1;
        }
        for (pi, slot) in adviser_slots {
            cloned.players[pi].advisers[slot] = hidden_deck_pool[cursor];
            cursor += 1;
        }

        // 2. Collect all unseen relics (relic_deck + unpeeked Reliquary + unpeeked site relics)
        let mut relic_pool: Vec<CardId> = cloned.relic_deck.clone();
        let mut reliquary_slots: Vec<usize> = Vec::new();
        for (slot, &rid) in cloned.reliquary.iter().enumerate() {
            if !kb.knows_reliquary(slot) {
                relic_pool.push(rid);
                reliquary_slots.push(slot);
            }
        }
        let mut site_relic_slots: Vec<(usize, usize)> = Vec::new();
        for si in 0..MAX_SITES {
            if !cloned.sites[si].is_faceup {
                continue;
            }
            for rslot in 0..cloned.sites[si].relics.len() {
                if !kb.knows_site_relic(si as SiteIndex, rslot) {
                    relic_pool.push(cloned.sites[si].relics[rslot]);
                    site_relic_slots.push((si, rslot));
                }
            }
        }
        rng.shuffle(&mut relic_pool);
        let mut rcursor = 0;
        for slot in &mut cloned.relic_deck {
            *slot = relic_pool[rcursor];
            rcursor += 1;
        }
        for slot in reliquary_slots {
            cloned.reliquary[slot] = relic_pool[rcursor];
            rcursor += 1;
        }
        for (si, rslot) in site_relic_slots {
            cloned.sites[si].relics[rslot] = relic_pool[rcursor];
            rcursor += 1;
        }

        // 3. Collect all unseen facedown sites (on map + site_deck)
        let mut site_pool: Vec<CardId> = cloned.site_deck.clone();
        let mut map_fd_sites: Vec<usize> = Vec::new();
        for si in 0..MAX_SITES {
            if !cloned.sites[si].is_faceup && (kb.known_facedown_sites_mask & (1u8 << si)) == 0 {
                site_pool.push(cloned.sites[si].site_id);
                map_fd_sites.push(si);
            }
        }
        rng.shuffle(&mut site_pool);
        let mut scursor = 0;
        for slot in &mut cloned.site_deck {
            *slot = site_pool[scursor];
            scursor += 1;
        }
        for si in map_fd_sites {
            let sid = site_pool[scursor];
            scursor += 1;
            cloned.sites[si].site_id = sid;
            cloned.sites[si].capacity = get_card(sid).capacity;
        }

        cloned
    }

    pub fn push_talk(&mut self, event: TalkEvent) {
        if self.talk_log.len() >= MAX_TALK_LOG {
            self.talk_log.pop_front();
        }
        self.talk_log.push_back(event);
    }
}

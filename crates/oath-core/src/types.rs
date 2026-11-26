use serde::{Deserialize, Serialize};

pub type CardId = u16;
pub type PlayerId = u8;
pub type SiteIndex = u8;
pub type ActionId = u16;

pub const MAX_PLAYERS: usize = 6;
pub const MAX_SITES: usize = 8;
pub const MAX_CARDS_PER_SITE: usize = 3;
pub const MAX_ADVISERS: usize = 3;
pub const MAX_RELIQUARY: usize = 4;
pub const MAX_ROUNDS: u8 = 8;
pub const MAX_VISIONS_DRAWN: u8 = 5;
pub const NUM_SUITS: usize = 6;
pub const NUM_REGIONS: usize = 3;
pub const MAX_WARBANDS_CHANCELLOR: u8 = 24;
pub const MAX_WARBANDS_EXILE: u8 = 14;
pub const MAX_SUPPLY: u8 = 9;
pub const MAX_FAVOR_TOTAL: u8 = 36;
pub const MAX_SECRETS_TOTAL: u8 = 20;
pub const MAX_TALK_PER_TURN: u8 = 3;
pub const MAX_DEAL_ROUNDS: u8 = 3;
pub const MAX_TALK_LOG: usize = 16;

// Special card IDs (exact OATH-XXX numbers)
pub const CARD_EMPTY: CardId = 0;
pub const CARD_UNKNOWN: CardId = 260; // Sentinel for hidden facedown cards in observations
pub const CARD_GRAND_SCEPTER: CardId = 231;
pub const CARD_CONSPIRACY: CardId = 232;
pub const CARD_VISION_FAITH: CardId = 233;
pub const CARD_VISION_REBELLION: CardId = 234;
pub const CARD_VISION_SANCTUARY: CardId = 235;
pub const CARD_VISION_CONQUEST: CardId = 236;

// Notable Site IDs
pub const SITE_ANCIENT_CITY: CardId = 237;
pub const SITE_BARREN_COAST: CardId = 238;
pub const SITE_BURIED_GIANT: CardId = 239;
pub const SITE_CHARMING_VALLEY: CardId = 240;
pub const SITE_DEEP_WOODS: CardId = 241;
pub const SITE_DROWNED_CITY: CardId = 242;
pub const SITE_FERTILE_VALLEY: CardId = 243;
pub const SITE_GREAT_SLUM: CardId = 244;
pub const SITE_THE_TRIBUNAL: CardId = 245;
pub const SITE_LUSH_COAST: CardId = 246;
pub const SITE_MARSHES: CardId = 247;
pub const SITE_MINE: CardId = 248;
pub const SITE_MOUNTAIN: CardId = 249;
pub const SITE_NARROW_PASS: CardId = 250;
pub const SITE_PLAINS: CardId = 251;
pub const SITE_RIVER: CardId = 252;
pub const SITE_ROCKY_COAST: CardId = 253;
pub const SITE_SALT_FLATS: CardId = 254;
pub const SITE_SHROUDED_WOOD: CardId = 255;
pub const SITE_STANDING_STONES: CardId = 256;
pub const SITE_STEPPE: CardId = 257;
pub const SITE_THE_HIDDEN_PLACE: CardId = 258;
pub const SITE_WASTES: CardId = 259;

// Notable Relic IDs
pub const RELIC_STICKY_FIRE: CardId = 211;
pub const RELIC_CURSED_CAULDRON: CardId = 212;
pub const RELIC_BRASS_HORSE: CardId = 213;
pub const RELIC_TRUTHFUL_HARP: CardId = 214;
pub const RELIC_GRAND_MASK: CardId = 215;
pub const RELIC_HORNED_MASK: CardId = 216;
pub const RELIC_CUP_OF_PLENTY: CardId = 217;
pub const RELIC_WHISTLE: CardId = 218;
pub const RELIC_DOWSING_STICKS: CardId = 219;
pub const RELIC_CRACKED_HORN: CardId = 220;
pub const RELIC_BANDIT_CROWN: CardId = 221;
pub const RELIC_RING_OF_DEVOTION: CardId = 222;
pub const RELIC_SKELETON_KEY: CardId = 223;
pub const RELIC_ORACULAR_PIG: CardId = 224;
pub const RELIC_CIRCLET_OF_COMMAND: CardId = 225;
pub const RELIC_IVORY_EYE: CardId = 226;
pub const RELIC_MAP: CardId = 227;
pub const RELIC_OBSIDIAN_CAGE: CardId = 228;
pub const RELIC_BOOK_OF_RECORDS: CardId = 229;
pub const RELIC_DRAGONSKIN_DRUM: CardId = 230;

// Edifice IDs
pub const EDIFICE_SPRAWLING_RAMPART: CardId = 199;
pub const EDIFICE_BANDIT_RAMPART: CardId = 200;
pub const EDIFICE_HALL_OF_DEBATE: CardId = 201;
pub const EDIFICE_HALL_OF_MOCKERY: CardId = 202;
pub const EDIFICE_FOREST_TEMPLE: CardId = 203;
pub const EDIFICE_RUINED_TEMPLE: CardId = 204;
pub const EDIFICE_FESTIVAL_DISTRICT: CardId = 205;
pub const EDIFICE_SQUALID_DISTRICT: CardId = 206;
pub const EDIFICE_GREAT_SPIRE: CardId = 207;
pub const EDIFICE_FALLEN_SPIRE: CardId = 208;
pub const EDIFICE_ANCIENT_FORGE: CardId = 209;
pub const EDIFICE_BROKEN_FORGE: CardId = 210;

// Tag bitflags
pub const TAG_POWER: u16 = 1 << 0;
pub const TAG_BATTLE_PLAN: u16 = 1 << 1;
pub const TAG_SEARCH: u16 = 1 << 2;
pub const TAG_TRAVEL: u16 = 1 << 3;
pub const TAG_CAMPAIGN: u16 = 1 << 4;
pub const TAG_TRADE: u16 = 1 << 5;
pub const TAG_MUSTER: u16 = 1 << 6;
pub const TAG_RECOVER: u16 = 1 << 7;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Suit {
    Discord = 0,
    Arcane = 1,
    Order = 2,
    Hearth = 3,
    Beast = 4,
    Nomad = 5,
}

impl Suit {
    pub const ALL: [Suit; 6] = [
        Suit::Discord,
        Suit::Arcane,
        Suit::Order,
        Suit::Hearth,
        Suit::Beast,
        Suit::Nomad,
    ];

    /// Clockwise suit order on the map (§8.4).
    pub const CLOCKWISE: [Suit; 6] = [
        Suit::Arcane,
        Suit::Beast,
        Suit::Discord,
        Suit::Hearth,
        Suit::Nomad,
        Suit::Order,
    ];

    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(Suit::Discord),
            1 => Some(Suit::Arcane),
            2 => Some(Suit::Order),
            3 => Some(Suit::Hearth),
            4 => Some(Suit::Beast),
            5 => Some(Suit::Nomad),
            _ => None,
        }
    }

    pub fn bit(self) -> u8 {
        1u8 << (self as u8)
    }

    pub fn name(self) -> &'static str {
        match self {
            Suit::Discord => "Discord",
            Suit::Arcane => "Arcane",
            Suit::Order => "Order",
            Suit::Hearth => "Hearth",
            Suit::Beast => "Beast",
            Suit::Nomad => "Nomad",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Region {
    Cradle = 0,
    Provinces = 1,
    Hinterland = 2,
}

impl Region {
    pub fn from_site_index(idx: SiteIndex) -> Self {
        match idx {
            0..=1 => Region::Cradle,
            2..=4 => Region::Provinces,
            _ => Region::Hinterland,
        }
    }

    /// Region whose discard pile receives cards discarded from this region (§5.1.3).
    pub fn discard_target(self) -> Self {
        match self {
            Region::Cradle => Region::Provinces,
            Region::Provinces => Region::Hinterland,
            Region::Hinterland => Region::Cradle,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Region::Cradle => "Cradle",
            Region::Provinces => "Provinces",
            Region::Hinterland => "Hinterland",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Role {
    Chancellor = 0,
    Exile = 1,
    Citizen = 2,
}

impl Role {
    pub fn is_imperial(self) -> bool {
        matches!(self, Role::Chancellor | Role::Citizen)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum OathGoal {
    Supremacy = 0,
    People = 1,
    Devotion = 2,
    Sanctuary = 3,
}

impl OathGoal {
    pub const ALL: [OathGoal; 4] = [
        OathGoal::Supremacy,
        OathGoal::People,
        OathGoal::Devotion,
        OathGoal::Sanctuary,
    ];

    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0 => Some(OathGoal::Supremacy),
            1 => Some(OathGoal::People),
            2 => Some(OathGoal::Devotion),
            3 => Some(OathGoal::Sanctuary),
            _ => None,
        }
    }

    pub fn successor_goal(self) -> SuccessorGoal {
        match self {
            OathGoal::Supremacy => SuccessorGoal::MostRelicsBanners,
            OathGoal::People => SuccessorGoal::DarkestSecret,
            OathGoal::Devotion => SuccessorGoal::GrandScepter,
            OathGoal::Sanctuary => SuccessorGoal::PeoplesFavor,
        }
    }

    pub fn from_vision(card_id: CardId) -> Option<Self> {
        match card_id {
            CARD_VISION_CONQUEST => Some(OathGoal::Supremacy),
            CARD_VISION_FAITH => Some(OathGoal::Devotion),
            CARD_VISION_REBELLION => Some(OathGoal::People),
            CARD_VISION_SANCTUARY => Some(OathGoal::Sanctuary),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum SuccessorGoal {
    MostRelicsBanners = 0,
    DarkestSecret = 1,
    PeoplesFavor = 2,
    GrandScepter = 3,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum WinType {
    OathkeeperDefault = 0,
    Usurper = 1,
    Vision = 2,
    Successor = 3,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum TitleSide {
    Oathkeeper = 0,
    Usurper = 1,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Banner {
    PeoplesFavor = 0,
    DarkestSecret = 1,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Phase {
    Wake = 0,
    Act = 1,
    Rest = 2,
    Chronicle = 3,
    GameOver = 4,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum CardType {
    Empty = 0,
    Denizen = 1,
    Edifice = 2,
    Relic = 3,
    Vision = 4,
    Site = 5,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum CardRestriction {
    None = 0,
    SiteOnly = 1,
    AdviserOnly = 2,
    Locked = 3,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum BattlePlanSide {
    None = 0,
    Attacker = 1,
    Defender = 2,
    Either = 3,
}

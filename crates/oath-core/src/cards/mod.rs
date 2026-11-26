use crate::types::{BattlePlanSide, CardId, CardRestriction, CardType, Suit};

pub mod denizens;
pub mod edifices;
pub mod relics;
pub mod sites;
pub mod visions;

#[derive(Debug, Clone, Copy)]
pub struct CardDef {
    pub id: CardId,
    pub leder_id: &'static str,
    pub name: &'static str,
    pub card_type: CardType,
    pub suit: Option<Suit>,
    pub edifice_suit: Option<Suit>,
    pub restriction: CardRestriction,
    pub capacity: u8,
    pub defense: u8,
    pub starting_relics: u8,
    pub starting_favor: u8,
    pub starting_secrets: u8,
    pub recover_favor: u8,
    pub recover_secrets: u8,
    pub is_coast: bool,
    pub edifice_is_ruined: bool,
    pub edifice_flip_id: Option<CardId>,
    pub battle_plan_side: BattlePlanSide,
    pub tag_bits: u16,
    pub cost_favor: u8,
    pub cost_secrets: u8,
    pub cost_burn_favor: u8,
    pub cost_burn_secrets: u8,
    pub effect_text: &'static str,
}

include!(concat!(env!("OUT_DIR"), "/card_defs_generated.rs"));

#[inline]
pub fn get_card(id: CardId) -> &'static CardDef {
    CARD_DEFS
        .get(id as usize)
        .unwrap_or(&CARD_DEFS[0])
}

pub fn is_denizen(id: CardId) -> bool {
    get_card(id).card_type == CardType::Denizen
}

pub fn is_edifice(id: CardId) -> bool {
    get_card(id).card_type == CardType::Edifice
}

pub fn is_relic(id: CardId) -> bool {
    get_card(id).card_type == CardType::Relic
}

pub fn is_vision(id: CardId) -> bool {
    get_card(id).card_type == CardType::Vision
}

pub fn is_site(id: CardId) -> bool {
    get_card(id).card_type == CardType::Site
}

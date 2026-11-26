use serde::Deserialize;
use std::env;
use std::fs;
use std::path::Path;

#[derive(Deserialize)]
struct ManifestCard {
    id: u16,
    leder_id: String,
    name: String,
    card_type: String,
    suit: Option<String>,
    edifice_suit: Option<String>,
    restriction: String,
    capacity: u8,
    defense: u8,
    starting_relics: u8,
    starting_favor: u8,
    starting_secrets: u8,
    recover_favor: u8,
    recover_secrets: u8,
    is_coast: bool,
    edifice_is_ruined: bool,
    edifice_flip_id: Option<u16>,
    battle_plan_side: String,
    effect_tags: Vec<String>,
    effect_text: String,
    cost_favor: u8,
    cost_secrets: u8,
    cost_burn_favor: u8,
    cost_burn_secrets: u8,
}

fn suit_expr(s: Option<&str>) -> &'static str {
    match s {
        Some("discord") => "Some(Suit::Discord)",
        Some("arcane") => "Some(Suit::Arcane)",
        Some("order") => "Some(Suit::Order)",
        Some("hearth") => "Some(Suit::Hearth)",
        Some("beast") => "Some(Suit::Beast)",
        Some("nomad") => "Some(Suit::Nomad)",
        _ => "None",
    }
}

fn ctype_expr(s: &str) -> &'static str {
    match s {
        "denizen" => "CardType::Denizen",
        "edifice" => "CardType::Edifice",
        "relic" => "CardType::Relic",
        "vision" => "CardType::Vision",
        "site" => "CardType::Site",
        _ => "CardType::Empty",
    }
}

fn restr_expr(s: &str) -> &'static str {
    match s {
        "site_only" => "CardRestriction::SiteOnly",
        "adviser_only" => "CardRestriction::AdviserOnly",
        "locked" => "CardRestriction::Locked",
        _ => "CardRestriction::None",
    }
}

fn bp_side_expr(s: &str) -> &'static str {
    match s {
        "attacker" => "BattlePlanSide::Attacker",
        "defender" => "BattlePlanSide::Defender",
        "either" => "BattlePlanSide::Either",
        _ => "BattlePlanSide::None",
    }
}

fn tag_bits(tags: &[String]) -> u16 {
    let mut bits = 0u16;
    for t in tags {
        match t.as_str() {
            "Power" => bits |= 1 << 0,
            "Battle Plan" => bits |= 1 << 1,
            "Search" => bits |= 1 << 2,
            "Travel" => bits |= 1 << 3,
            "Campaign" => bits |= 1 << 4,
            "Trade" => bits |= 1 << 5,
            "Muster" => bits |= 1 << 6,
            "Recover" => bits |= 1 << 7,
            _ => {}
        }
    }
    bits
}

fn main() {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let json_path = Path::new(&manifest_dir)
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("data")
        .join("cards_manifest.json");
    println!("cargo:rerun-if-changed={}", json_path.display());

    let raw = fs::read_to_string(&json_path).expect("failed to read data/cards_manifest.json");
    let cards: Vec<ManifestCard> = serde_json::from_str(&raw).expect("invalid cards_manifest.json");
    assert_eq!(cards.len(), 259, "Expected 259 cards in manifest");

    let mut out = String::new();
    out.push_str("pub const NUM_CARDS: usize = 259;\n");
    out.push_str("pub const CARD_DEFS: [CardDef; 260] = [\n");
    out.push_str(
        "    CardDef {\n\
         \x20       id: 0,\n\
         \x20       leder_id: \"EMPTY\",\n\
         \x20       name: \"Empty\",\n\
         \x20       card_type: CardType::Empty,\n\
         \x20       suit: None,\n\
         \x20       edifice_suit: None,\n\
         \x20       restriction: CardRestriction::None,\n\
         \x20       capacity: 0,\n\
         \x20       defense: 0,\n\
         \x20       starting_relics: 0,\n\
         \x20       starting_favor: 0,\n\
         \x20       starting_secrets: 0,\n\
         \x20       recover_favor: 0,\n\
         \x20       recover_secrets: 0,\n\
         \x20       is_coast: false,\n\
         \x20       edifice_is_ruined: false,\n\
         \x20       edifice_flip_id: None,\n\
         \x20       battle_plan_side: BattlePlanSide::None,\n\
         \x20       tag_bits: 0,\n\
         \x20       cost_favor: 0,\n\
         \x20       cost_secrets: 0,\n\
         \x20       cost_burn_favor: 0,\n\
         \x20       cost_burn_secrets: 0,\n\
         \x20       effect_text: \"\",\n\
         \x20   },\n",
    );

    for (idx, c) in cards.iter().enumerate() {
        assert_eq!(c.id as usize, idx + 1, "Manifest must be sorted 1..=259");
        let flip = match c.edifice_flip_id {
            Some(id) => format!("Some({id})"),
            None => "None".to_string(),
        };
        out.push_str(&format!(
            "    CardDef {{\n\
             \x20       id: {},\n\
             \x20       leder_id: {:?},\n\
             \x20       name: {:?},\n\
             \x20       card_type: {},\n\
             \x20       suit: {},\n\
             \x20       edifice_suit: {},\n\
             \x20       restriction: {},\n\
             \x20       capacity: {},\n\
             \x20       defense: {},\n\
             \x20       starting_relics: {},\n\
             \x20       starting_favor: {},\n\
             \x20       starting_secrets: {},\n\
             \x20       recover_favor: {},\n\
             \x20       recover_secrets: {},\n\
             \x20       is_coast: {},\n\
             \x20       edifice_is_ruined: {},\n\
             \x20       edifice_flip_id: {},\n\
             \x20       battle_plan_side: {},\n\
             \x20       tag_bits: {},\n\
             \x20       cost_favor: {},\n\
             \x20       cost_secrets: {},\n\
             \x20       cost_burn_favor: {},\n\
             \x20       cost_burn_secrets: {},\n\
             \x20       effect_text: {:?},\n\
             \x20   }},\n",
            c.id,
            c.leder_id,
            c.name,
            ctype_expr(&c.card_type),
            suit_expr(c.suit.as_deref()),
            suit_expr(c.edifice_suit.as_deref()),
            restr_expr(&c.restriction),
            c.capacity,
            c.defense,
            c.starting_relics,
            c.starting_favor,
            c.starting_secrets,
            c.recover_favor,
            c.recover_secrets,
            c.is_coast,
            c.edifice_is_ruined,
            flip,
            bp_side_expr(&c.battle_plan_side),
            tag_bits(&c.effect_tags),
            c.cost_favor,
            c.cost_secrets,
            c.cost_burn_favor,
            c.cost_burn_secrets,
            c.effect_text,
        ));
    }
    out.push_str("];\n");

    let out_dir = env::var("OUT_DIR").unwrap();
    let dest_path = Path::new(&out_dir).join("card_defs_generated.rs");
    fs::write(dest_path, out).expect("failed to write generated card defs");
}

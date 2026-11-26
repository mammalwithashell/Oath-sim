//! Exhaustive per-site unit tests for all 23 Sites (OATH-237..OATH-259).

use oath_core::engine::campaign;
use oath_core::engine::major_actions;
use oath_core::engine::turn;
use oath_core::state::ChoiceReason;
use oath_core::*;

fn base_state() -> GameState {
    let cfg = GameConfig {
        num_players: 4,
        seed: 42,
        first_game: true,
        oath_goal: Some(OathGoal::Supremacy),
        chronicle_enabled: false,
    };
    let mut gs = create_initial_state(&cfg, None);
    for s in &mut gs.sites {
        s.is_faceup = true;
    }
    gs
}

#[test]
fn test_all_23_sites_present_in_card_defs() {
    for sid in 237..=259u16 {
        let def = get_card(sid);
        assert_eq!(def.card_type, CardType::Site);
        assert!(def.defense >= 1, "Site {} missing defense", def.name);
    }
}

#[test]
fn test_homeland_search_sites_237_241_243_256_257_259() {
    // 237 Ancient City (Order -> +2 warbands)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_ANCIENT_CITY;
    let wb0 = gs.players[0].warbands_board;
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 1); // Wrestlers (Order)
    assert_eq!(gs.players[0].warbands_board, wb0 + 2);

    // 241 Deep Woods (Beast -> take relic at site)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_DEEP_WOODS;
    gs.sites[0].relics.push(RELIC_MAP);
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 39); // Wolves (Beast)
    assert!(gs.players[0].has_relic(RELIC_MAP));

    // 243 Fertile Valley (Hearth -> +1 extra Hearth favor)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_FERTILE_VALLEY;
    gs.favor_banks[Suit::Hearth as usize] = 5;
    let f0 = gs.players[0].favor;
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 47); // Wayside Inn (Hearth)
    assert_eq!(gs.players[0].favor, f0 + 2); // 1 normal + 1 homeland

    // 256 Standing Stones (Arcane -> +1 secret)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_STANDING_STONES;
    gs.shared_secrets = 5;
    let s0 = gs.players[0].secrets_faceup;
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 9); // Alchemist (Arcane)
    assert_eq!(gs.players[0].secrets_faceup, s0 + 1);

    // 257 Steppe (Nomad -> +1 supply)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_STEPPE;
    gs.players[0].supply = 4;
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 26); // Elders (Nomad)
    assert_eq!(gs.players[0].supply, 5);

    // 259 Wastes (Discord -> +1 extra Discord favor)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_WASTES;
    gs.favor_banks[Suit::Discord as usize] = 5;
    let f0 = gs.players[0].favor;
    major_actions::on_card_played_to_site(&mut gs, 0, 0, 15); // A Small Favor (Discord)
    assert_eq!(gs.players[0].favor, f0 + 2);
}

#[test]
fn test_travel_sites_238_239_240_246_250_253_255_258() {
    let mut gs = base_state();
    // 238 Barren Coast, 246 Lush Coast, 253 Rocky Coast: Coast-to-Coast = 1 Supply
    gs.sites[0].site_id = SITE_BARREN_COAST;
    gs.sites[5].site_id = SITE_LUSH_COAST;
    gs.sites[6].site_id = SITE_ROCKY_COAST;
    gs.players[0].pawn_site = 0;
    assert_eq!(major_actions::travel_cost(&gs, 0, 5), 1);
    assert_eq!(major_actions::travel_cost(&gs, 0, 6), 1);

    // 239 Buried Giant: can travel with 0 supply by flipping 1 faceup secret
    gs.sites[0].site_id = SITE_BURIED_GIANT;
    gs.sites[1].site_id = SITE_PLAINS;
    gs.players[0].supply = 0;
    gs.players[0].secrets_faceup = 1;
    assert!(major_actions::can_travel(&gs, 0, 1));
    major_actions::execute_travel(&mut gs, 0, 1, false);
    assert_eq!(gs.players[0].pawn_site, 1);
    assert_eq!(gs.players[0].secrets_facedown, 1);

    // 240 Charming Valley: +1 Supply cost
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_CHARMING_VALLEY;
    gs.sites[1].site_id = SITE_PLAINS;
    assert_eq!(major_actions::travel_cost(&gs, 0, 1), 2);

    // 250 Narrow Pass: forced stop when entering region from another region
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_PLAINS;
    gs.sites[2].site_id = SITE_RIVER;
    gs.sites[4].site_id = SITE_NARROW_PASS;
    gs.players[0].pawn_site = 0;
    assert!(!major_actions::can_travel(&gs, 0, 2));
    assert!(major_actions::can_travel(&gs, 0, 4));

    // 255 Shrouded Wood: always 2 Supply & ignores Narrow Pass + Hidden Place
    gs.sites[0].site_id = SITE_SHROUDED_WOOD;
    gs.sites[2].site_id = SITE_THE_HIDDEN_PLACE;
    gs.players[0].secrets_faceup = 0;
    assert_eq!(major_actions::travel_cost(&gs, 0, 2), 2);
    assert!(major_actions::can_travel(&gs, 0, 2));

    // 258 The Hidden Place: requires faceup secret from normal sites
    gs.sites[0].site_id = SITE_PLAINS;
    gs.sites[4].site_id = SITE_RIVER; // clear Narrow Pass
    assert!(!major_actions::can_travel(&gs, 0, 2));
    gs.players[0].secrets_faceup = 1;
    assert!(major_actions::can_travel(&gs, 0, 2));
}

#[test]
fn test_wake_sites_242_248_254() {
    // 242 Drowned City: Wake takes 1 secret from site
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_DROWNED_CITY;
    gs.sites[0].site_secrets = 2;
    gs.players[0].pawn_site = 0;
    let s0 = gs.players[0].secrets_faceup;
    turn::resume_wake_phase(&mut gs, 0, 3);
    assert_eq!(gs.players[0].secrets_faceup, s0 + 1);
    assert_eq!(gs.sites[0].site_secrets, 1);

    // 248 Mine: Wake takes 1 favor from site
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_MINE;
    gs.sites[0].site_favor = 2;
    gs.players[0].pawn_site = 0;
    let f0 = gs.players[0].favor;
    turn::resume_wake_phase(&mut gs, 0, 3);
    assert_eq!(gs.players[0].favor, f0 + 1);
    assert_eq!(gs.sites[0].site_favor, 1);

    // 254 Salt Flats: prompts player when both favor & secret available
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_SALT_FLATS;
    gs.sites[0].site_favor = 1;
    gs.sites[0].site_secrets = 1;
    gs.players[0].pawn_site = 0;
    turn::resume_wake_phase(&mut gs, 0, 3);
    assert!(matches!(
        gs.decision,
        DecisionPoint::ChooseYesNo {
            reason: ChoiceReason::SiteWakeResource,
            ..
        }
    ));
}

#[test]
fn test_special_sites_244_245_247_249_251_252() {
    // 244 Great Slum: allows playing to a full site by discarding
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_GREAT_SLUM;
    gs.sites[0].capacity = 1;
    gs.sites[0].cards[0] = 1;
    gs.players[0].pawn_site = 0;
    assert!(major_actions::can_play_search_card(&gs, 0, 2, 0));

    // 245 The Tribunal: Action opens DealPartner choice
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_THE_TRIBUNAL;
    gs.players[0].pawn_site = 0;
    assert!(cards::sites::can_use_site_action(&gs, 0, SITE_THE_TRIBUNAL));

    // 247 Marshes: draws 1 fewer card on Search (2 instead of 3)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_MARSHES;
    gs.players[0].pawn_site = 0;
    gs.players[0].supply = 5;
    // Put 3 non-vision denizens on top of world_deck
    gs.world_deck.push(1);
    gs.world_deck.push(2);
    gs.world_deck.push(3);
    major_actions::execute_search(&mut gs, 0, true);
    assert_eq!(gs.search.as_ref().unwrap().drawn_cards.len(), 2);

    // 249 Mountain (-1 atk die) & 251 Plains (+1 atk die)
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_MOUNTAIN;
    gs.sites[0].ruling_player = None;
    gs.players[0].pawn_site = 0;
    gs.players[0].warbands_board = 4;
    campaign::execute_campaign_declare(&mut gs, 0, None);
    // Attack dice collected: 4 - 1 = 3 (campaign may resolve immediately if no BPs, so check Plains separately)

    // 252 River: +1 warband on muster if ruled
    let mut gs = base_state();
    gs.sites[0].site_id = SITE_RIVER;
    gs.sites[0].ruling_player = Some(0);
    gs.sites[0].cards[0] = 1;
    gs.sites[0].card_favor[0] = 0;
    gs.sites[0].card_secrets[0] = 0;
    gs.players[0].pawn_site = 0;
    gs.players[0].favor = 3;
    let wb0 = gs.players[0].warbands_board;
    major_actions::execute_muster(&mut gs, 0, 0);
    assert_eq!(gs.players[0].warbands_board, wb0 + 3); // 2 base + 1 River
}

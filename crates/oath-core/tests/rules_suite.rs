use oath_core::agents::{heuristic_agent_action, random_agent_action};
use oath_core::engine::campaign;
use oath_core::engine::major_actions;
use oath_core::*;

#[test]
fn test_site_powers_travel_and_homeland() {
    let cfg = GameConfig {
        num_players: 4,
        seed: 101,
        first_game: true,
        oath_goal: Some(OathGoal::Supremacy),
        chronicle_enabled: false,
    };
    let mut gs = create_initial_state(&cfg, None);
    // Test Coast-to-Coast = 1 supply (Rocky Coast=2, Lush Coast=3)
    gs.sites[2].site_id = SITE_ROCKY_COAST;
    gs.sites[2].is_faceup = true;
    gs.sites[3].site_id = SITE_LUSH_COAST;
    gs.sites[3].is_faceup = true;
    gs.players[0].pawn_site = 2;
    assert_eq!(major_actions::travel_cost(&gs, 0, 3), 1);

    // Test Shrouded Wood = 2 supply from anywhere & ignores Narrow Pass
    gs.sites[0].site_id = SITE_SHROUDED_WOOD;
    gs.sites[0].is_faceup = true;
    gs.sites[4].site_id = SITE_NARROW_PASS;
    gs.sites[4].is_faceup = true;
    gs.players[0].pawn_site = 0;
    assert_eq!(major_actions::travel_cost(&gs, 0, 3), 2);
    assert!(major_actions::can_travel(&gs, 0, 3)); // Ignores Narrow Pass at site 4!

    // Without Shrouded Wood, traveling Cradle -> Provinces MUST go to Narrow Pass (site 4)
    gs.sites[0].site_id = SITE_PLAINS;
    assert!(!major_actions::can_travel(&gs, 0, 3));
    assert!(major_actions::can_travel(&gs, 0, 4));

    // Test Charming Valley +1 travel cost
    gs.sites[0].site_id = SITE_CHARMING_VALLEY;
    assert_eq!(major_actions::travel_cost(&gs, 0, 1), 2); // Cradle->Cradle base 1 + 1

    // Test Hidden Place requires faceup secret
    gs.sites[1].site_id = SITE_THE_HIDDEN_PLACE;
    gs.sites[1].is_faceup = true;
    gs.players[0].secrets_faceup = 0;
    assert!(!major_actions::can_travel(&gs, 0, 1));
    gs.players[0].secrets_faceup = 1;
    assert!(major_actions::can_travel(&gs, 0, 1));
}

#[test]
fn test_relics_faithfulness() {
    let cfg = GameConfig::default();
    let mut gs = create_initial_state(&cfg, None);

    // Dragonskin Drum: +1 warband on travel
    gs.players[0].relics.push(RELIC_DRAGONSKIN_DRUM);
    let wb_before = gs.players[0].warbands_board;
    gs.players[0].pawn_site = 0;
    step(&mut gs, encode_action(Action::Travel(1))).unwrap();
    assert_eq!(gs.players[0].warbands_board, wb_before + 1);

    // Map: return to bottom of relic deck for +4 supply
    gs.players[0].supply = 2;
    gs.players[0].relics.push(RELIC_MAP);
    let map_slot = gs.players[0].relics.iter().position(|&r| r == RELIC_MAP).unwrap() as u8;
    step(&mut gs, encode_action(Action::UseCardAction(7 + map_slot))).unwrap();
    assert_eq!(gs.players[0].supply, 6);
    assert!(!gs.players[0].has_relic(RELIC_MAP));
    assert_eq!(gs.relic_deck[0], RELIC_MAP);

    // Oracular Pig: peek top 3 of world deck
    gs.players[0].relics.push(RELIC_ORACULAR_PIG);
    let pig_slot = gs.players[0].relics.iter().position(|&r| r == RELIC_ORACULAR_PIG).unwrap() as u8;
    step(&mut gs, encode_action(Action::UseCardAction(7 + pig_slot))).unwrap();
    assert_eq!(gs.knowledge[0].known_world_deck_top.len(), 3);

    // Ring of Devotion: +2 warbands when mustering, cannot place warbands at sites
    gs.players[0].relics.push(RELIC_RING_OF_DEVOTION);
    assert!(!engine::minor_actions::can_move_warbands_to_site(&gs, 0));

    // Circlet of Command: protects banners from recovery
    gs.peoples_favor_holder = Some(1);
    gs.peoples_favor_tokens = 1;
    gs.players[0].favor = 5;
    gs.players[1].relics.push(RELIC_CIRCLET_OF_COMMAND);
    assert!(!major_actions::can_recover_peoples_favor(&gs, 0));
}

#[test]
fn test_edifices_faithfulness() {
    let cfg = GameConfig::default();
    let mut gs = create_initial_state(&cfg, None);

    // Hall of Debate blocks targeting People's Favor in campaign
    gs.sites[0].cards[0] = EDIFICE_HALL_OF_DEBATE;
    gs.peoples_favor_holder = Some(1);
    gs.players[0].pawn_site = 0;
    gs.players[1].pawn_site = 0;
    campaign::execute_campaign_declare(&mut gs, 0, Some(1));
    assert!(!campaign::can_target_banner(&gs, Banner::PeoplesFavor));

    // Broken Forge flips to Ancient Forge
    let mut gs2 = create_initial_state(&cfg, None);
    gs2.sites[0].cards[0] = EDIFICE_BROKEN_FORGE;
    gs2.players[0].pawn_site = 0;
    step(&mut gs2, encode_action(Action::UseCardAction(0))).unwrap();
    assert_eq!(gs2.sites[0].cards[0], EDIFICE_ANCIENT_FORGE);
}

#[test]
fn test_vision_and_usurper_wins() {
    let cfg = GameConfig::default();
    let mut gs = create_initial_state(&cfg, None);

    // Visionary win requires >= 3 visions drawn and meeting goal
    gs.players[1].revealed_vision = Some(CARD_VISION_REBELLION);
    gs.peoples_favor_holder = Some(1);
    gs.visions_drawn = 2;
    assert!(!engine::win::meets_vision_goal(&gs, 1));
    gs.visions_drawn = 3;
    assert!(engine::win::meets_vision_goal(&gs, 1));

    // Usurper win
    let mut gs2 = create_initial_state(&cfg, None);
    gs2.oathkeeper_holder = Some(1);
    gs2.oathkeeper_side = TitleSide::Usurper;
    assert!(engine::win::check_start_of_turn_wins(&mut gs2, 1));
    assert_eq!(gs2.winner, Some(1));
    assert_eq!(gs2.win_type, Some(WinType::Usurper));
}

#[test]
fn test_campaign_full_flow_and_banish() {
    let cfg = GameConfig::default();
    let mut gs = create_initial_state(&cfg, None);
    gs.players[0].pawn_site = 0;
    gs.players[1].pawn_site = 0;
    gs.players[0].warbands_board = 10;
    gs.players[1].warbands_board = 0;
    gs.players[1].favor = 4;

    // Campaign against Player 1 (rel=1)
    step(&mut gs, encode_action(Action::CampaignDeclare(1))).unwrap();
    step(&mut gs, encode_action(Action::CampaignTargetPawn)).unwrap();
    step(&mut gs, encode_action(Action::Confirm)).unwrap();

    // Finish battle plans / reactive talk / sacrifice / banish cleanly
    let mut rng = FastRng::seed_from_u64(7);
    let mut steps = 0;
    while !matches!(gs.decision, DecisionPoint::TurnAct { .. }) && !gs.is_game_over && steps < 50 {
        let act = heuristic_agent_action(&gs, &mut rng);
        step(&mut gs, act).unwrap();
        steps += 1;
    }
    assert!(steps < 50);
}

#[test]
fn test_chronicle_5_game_lineage() {
    let mut ch: Option<ChronicleState> = None;
    for game_idx in 0..5u64 {
        let cfg = GameConfig {
            num_players: 4,
            seed: 500 + game_idx,
            first_game: game_idx == 0,
            oath_goal: None,
            chronicle_enabled: true,
        };
        let mut gs = create_initial_state(&cfg, ch.as_ref());
        let mut rng = FastRng::seed_from_u64(1000 + game_idx);
        while !gs.is_game_over {
            let act = heuristic_agent_action(&gs, &mut rng);
            step(&mut gs, act).unwrap();
        }
        assert!(gs.winner.is_some());
        ch = Some(apply_chronicle(&mut gs));
    }
    let final_ch = ch.unwrap();
    assert!(!final_ch.world_deck.is_empty());
    assert!(!final_ch.relic_deck.is_empty());
}

#[test]
fn test_observation_finite_and_determinize_invariants() {
    let cfg = GameConfig {
        num_players: 5,
        seed: 777,
        first_game: false,
        oath_goal: Some(OathGoal::Sanctuary),
        chronicle_enabled: false,
    };
    let gs = create_initial_state(&cfg, None);
    for p in 0..5u8 {
        let obs = encode_observation(&gs, p);
        assert!(obs.obs_flat.iter().all(|x| x.is_finite()));
        let mut rng = FastRng::seed_from_u64(100 + p as u64);
        let det = gs.determinize(p, &mut rng);
        assert_eq!(det.players[p as usize].advisers, gs.players[p as usize].advisers);
        assert_eq!(det.world_deck.len(), gs.world_deck.len());
        assert_eq!(det.relic_deck.len(), gs.relic_deck.len());
    }
}

#[test]
fn test_fuzz_500_games_all_player_counts() {
    for seed in 0..500u64 {
        let cfg = GameConfig {
            num_players: (2 + (seed % 5)) as u8,
            seed: seed.wrapping_mul(17) + 1,
            first_game: seed % 3 == 0,
            oath_goal: Some(OathGoal::ALL[(seed % 4) as usize]),
            chronicle_enabled: false,
        };
        let mut gs = create_initial_state(&cfg, None);
        let mut rng = FastRng::seed_from_u64(seed ^ 0xDEAD_BEEF);
        while !gs.is_game_over {
            let act = if seed % 2 == 0 {
                heuristic_agent_action(&gs, &mut rng)
            } else {
                random_agent_action(&gs, &mut rng)
            };
            step(&mut gs, act).unwrap();
        }
        assert!(gs.winner.is_some());
    }
}

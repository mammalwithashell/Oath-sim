//! Exhaustive Denizen test suite covering all 198 Denizens (OATH-001..OATH-198).

use oath_core::cards::denizens;
use oath_core::engine::{campaign, major_actions, minor_actions, turn, win};
use oath_core::*;

fn fresh_gs() -> GameState {
    let cfg = GameConfig {
        num_players: 4,
        seed: 77,
        first_game: true,
        oath_goal: Some(OathGoal::Supremacy),
        chronicle_enabled: false,
    };
    let mut gs = create_initial_state(&cfg, None);
    for s in &mut gs.sites {
        s.is_faceup = true;
    }
    gs.players[0].favor = 6;
    gs.players[0].secrets_faceup = 5;
    gs.players[0].warbands_board = 6;
    gs.players[1].favor = 6;
    gs.players[1].secrets_faceup = 5;
    gs.players[1].warbands_board = 6;
    gs.players[0].pawn_site = 0;
    gs.players[1].pawn_site = 0;
    gs
}

#[test]
fn test_all_198_denizens_parametric_lifecycle_no_panics() {
    // Exercise every single Denizen ID 1..=198 across:
    // - CardDef lookup & suit/type validity
    // - trigger_when_played
    // - can_use_denizen_action + execute_denizen_action (when eligible)
    // - apply_battle_plan + apply_post_combat_victory (for Battle Plans)
    // - trigger_rest_powers
    // - observation encoding finiteness
    for cid in 1..=198u16 {
        let def = get_card(cid);
        assert_eq!(def.card_type, CardType::Denizen, "Card {} should be Denizen", cid);
        assert!(def.suit.is_some(), "Denizen {} ({}) missing suit", cid, def.name);

        let mut gs = fresh_gs();
        gs.sites[0].cards[0] = cid;
        gs.players[0].advisers[0] = cid;
        gs.players[0].adviser_faceup[0] = true;

        // 1. When played
        denizens::trigger_when_played(&mut gs, 0, cid);

        // 2. Action power (if usable)
        if denizens::can_use_denizen_action(&gs, 0, cid) {
            denizens::execute_denizen_action(&mut gs, 0, cid);
        }

        // 3. Battle plan (if tagged)
        if (def.tag_bits & TAG_BATTLE_PLAN) != 0 {
            let mut cgs = fresh_gs();
            cgs.campaign = Some(oath_core::state::CampaignState::new(0, Some(1)));
            denizens::apply_battle_plan(&mut cgs, 0, true, cid);
            denizens::apply_post_combat_victory(&mut cgs, 0, true, cid);
        }

        // 4. Rest power
        denizens::trigger_rest_powers(&mut gs, 0);

        // 5. Observation remains finite
        let obs = encode_observation(&gs, 0);
        assert!(
            obs.obs_flat.iter().all(|x| x.is_finite()),
            "Non-finite observation after denizen {} ({})",
            cid,
            def.name
        );
    }
}

#[test]
fn test_key_denizen_actions_faithfulness() {
    // 9 Alchemist: gain 4 favor from banks
    let mut gs = fresh_gs();
    let f0 = gs.players[0].favor;
    denizens::execute_denizen_action(&mut gs, 0, 9);
    assert_eq!(gs.players[0].favor, f0 + 4);

    // 47 Wayside Inn: +2 Supply
    let mut gs = fresh_gs();
    gs.players[0].supply = 3;
    denizens::execute_denizen_action(&mut gs, 0, 47);
    assert_eq!(gs.players[0].supply, 5);

    // 62 Blood Pact: sacrifice 2 warbands -> +1 secret
    let mut gs = fresh_gs();
    let wb0 = gs.players[0].warbands_board;
    let s0 = gs.players[0].secrets_faceup;
    denizens::execute_denizen_action(&mut gs, 0, 62);
    assert_eq!(gs.players[0].warbands_board, wb0 - 2);
    assert_eq!(gs.players[0].secrets_faceup, s0 + 1);

    // 69 Tutor: +1 secret
    let mut gs = fresh_gs();
    let s0 = gs.players[0].secrets_faceup;
    denizens::execute_denizen_action(&mut gs, 0, 69);
    assert_eq!(gs.players[0].secrets_faceup, s0 + 1);

    // 131 Charming Friend: take 1 favor from player at site
    let mut gs = fresh_gs();
    let f0 = gs.players[0].favor;
    let f1 = gs.players[1].favor;
    denizens::execute_denizen_action(&mut gs, 0, 131);
    assert_eq!(gs.players[0].favor, f0 + 1);
    assert_eq!(gs.players[1].favor, f1 - 1);

    // 151 Convoys: merge another region's discard pile onto current region's
    let mut gs = fresh_gs();
    gs.discard_piles[0].clear();
    gs.discard_piles[1] = vec![1, 2, 3];
    denizens::execute_denizen_action(&mut gs, 0, 151);
    assert_eq!(gs.discard_piles[0], vec![1, 2, 3]);
    assert!(gs.discard_piles[1].is_empty());
}

#[test]
fn test_key_denizen_when_played_and_rest_faithfulness() {
    // 15 A Small Favor: +4 warbands
    let mut gs = fresh_gs();
    let wb0 = gs.players[0].warbands_board;
    denizens::trigger_when_played(&mut gs, 0, 15);
    assert_eq!(gs.players[0].warbands_board, wb0 + 4);

    // 28 Faithful Friend: +4 Supply
    let mut gs = fresh_gs();
    gs.players[0].supply = 2;
    denizens::trigger_when_played(&mut gs, 0, 28);
    assert_eq!(gs.players[0].supply, 6);

    // 79 Charlatan: burn all secrets but 1 from Darkest Secret
    let mut gs = fresh_gs();
    gs.darkest_secret_tokens = 5;
    denizens::trigger_when_played(&mut gs, 0, 79);
    assert_eq!(gs.darkest_secret_tokens, 1);

    // 147 Salad Days: +3 favor from 3 different banks
    let mut gs = fresh_gs();
    let f0 = gs.players[0].favor;
    denizens::trigger_when_played(&mut gs, 0, 147);
    assert_eq!(gs.players[0].favor, f0 + 3);

    // 97 Insomnia (Rest): +1 secret
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 97;
    gs.players[0].adviser_faceup[0] = true;
    let s0 = gs.players[0].secrets_faceup;
    denizens::trigger_rest_powers(&mut gs, 0);
    assert_eq!(gs.players[0].secrets_faceup, s0 + 1);

    // 193 Vow of Poverty (Rest): if 0 favor, +2 favor
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 193;
    gs.players[0].adviser_faceup[0] = true;
    gs.players[0].favor = 0;
    denizens::trigger_rest_powers(&mut gs, 0);
    assert_eq!(gs.players[0].favor, 2);
}

#[test]
fn test_persistent_denizens_blockers_and_modifiers() {
    // 148 Marriage: counts as 2 Hearth advisers
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 148;
    gs.players[0].adviser_faceup[0] = true;
    assert_eq!(gs.players[0].faceup_adviser_suit_count(Suit::Hearth), 2);

    // 123 Council Seat: Citizen cannot be exiled or self-exile
    let mut gs = fresh_gs();
    gs.players[1].role = Role::Citizen;
    gs.players[1].advisers[0] = 123;
    gs.players[1].adviser_faceup[0] = true;
    assert!(!minor_actions::can_exile_citizen(&gs, 0, 1));
    assert!(!minor_actions::can_self_exile(&gs, 1));

    // 145 Vow of Peace: cannot campaign
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 145;
    gs.players[0].adviser_faceup[0] = true;
    assert!(!campaign::can_campaign_player(&gs, 0, 1));
    assert!(!campaign::can_campaign_bandits(&gs, 0));

    // 74 Vow of Silence: cannot recover Darkest Secret
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 74;
    gs.players[0].adviser_faceup[0] = true;
    assert!(!major_actions::can_recover_darkest_secret(&gs, 0));

    // 86 Vow of Renewal: cannot recover People's Favor
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 86;
    gs.players[0].adviser_faceup[0] = true;
    assert!(!major_actions::can_recover_peoples_favor(&gs, 0));

    // 110 Tome Guardians: enemies cannot recover Darkest Secret
    let mut gs = fresh_gs();
    gs.players[1].advisers[0] = 110;
    gs.players[1].adviser_faceup[0] = true;
    assert!(!major_actions::can_recover_darkest_secret(&gs, 0));

    // 40 Animal Playmates: 0 supply muster on Beast card
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 40;
    gs.players[0].adviser_faceup[0] = true;
    assert_eq!(major_actions::muster_supply_cost(&gs, 0, 39), 0); // Wolves (Beast)
    assert_eq!(major_actions::muster_supply_cost(&gs, 0, 1), 1);  // Wrestlers (Order)

    // 176 Birdsong: 0 supply trade on Beast/Nomad card
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 176;
    gs.players[0].adviser_faceup[0] = true;
    assert_eq!(major_actions::trade_supply_cost(&gs, 0, 39), 0); // Beast
    assert_eq!(major_actions::trade_supply_cost(&gs, 0, 26), 0); // Nomad

    // 101 Chaos Cult: takes 1 favor when another player takes Oathkeeper
    let mut gs = fresh_gs();
    gs.players[1].advisers[0] = 101;
    gs.players[1].adviser_faceup[0] = true;
    gs.oathkeeper_holder = Some(0);
    let f1 = gs.players[1].favor;
    let f2 = gs.players[2].favor;
    gs.players[2].favor = 3;
    win::transfer_oathkeeper(&mut gs, 2);
    assert_eq!(gs.players[1].favor, f1 + 1);
    assert_eq!(gs.players[2].favor, 2);
    let _ = f2;

    // 173 Relic Worship: +3 supply after recovering relic
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 173;
    gs.players[0].adviser_faceup[0] = true;
    gs.players[0].supply = 3;
    gs.sites[0].relics.push(RELIC_MAP);
    major_actions::execute_recover_relic(&mut gs, 0, 0);
    assert_eq!(gs.players[0].supply, 5); // 3 - 1 + 3 = 5

    // 185 Vow of Union: cannot travel from ruled site if warbands on board
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 185;
    gs.players[0].adviser_faceup[0] = true;
    gs.sites[0].ruling_player = Some(0);
    gs.players[0].warbands_board = 2;
    assert!(!major_actions::can_travel(&gs, 0, 1));
    gs.players[0].warbands_board = 0;
    assert!(major_actions::can_travel(&gs, 0, 1));

    // 29 Tents: 0 supply travel in same region
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 29;
    gs.players[0].adviser_faceup[0] = true;
    assert_eq!(major_actions::travel_cost(&gs, 0, 1), 0);

    // 99 Gossip: enemies cannot play facedown advisers
    let mut gs = fresh_gs();
    gs.players[1].advisers[0] = 99;
    gs.players[1].adviser_faceup[0] = true;
    assert!(!major_actions::can_play_search_card(&gs, 0, 1, 2));

    // 134 News from Afar: search deck costs min 1
    let mut gs = fresh_gs();
    gs.players[0].advisers[0] = 134;
    gs.players[0].adviser_faceup[0] = true;
    assert_eq!(major_actions::search_deck_cost(&gs, 0), 1);

    let _ = turn::supply_from_bank(14, false);
}

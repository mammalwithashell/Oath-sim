pub mod actions;
pub mod agents;
pub mod cards;
pub mod engine;
pub mod obs;
pub mod rng;
pub mod state;
pub mod types;
pub mod vec_env;

pub use actions::{decode_action, describe_action, encode_action, Action, NUM_ACTIONS};
pub use cards::{get_card, CardDef, CARD_DEFS, NUM_CARDS};
pub use engine::{
    chronicle::apply_chronicle,
    legal_mask,
    setup::{create_initial_state, GameConfig},
    step,
};
pub use obs::{encode_observation, Observation, OBS_CARD_IDS_SIZE, OBS_FLAT_SIZE};
pub use rng::FastRng;
pub use state::{ChronicleState, DecisionPoint, GameState};
pub use types::*;
pub use vec_env::VecOathEnv;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agents::{heuristic_agent_action, random_agent_action};

    #[test]
    fn test_all_259_cards_loaded_and_implemented() {
        assert_eq!(NUM_CARDS, 259);
        for id in 1..=259u16 {
            let def = get_card(id);
            assert_eq!(def.id, id);
            assert!(!def.name.is_empty());
            assert!(
                cards::denizens::is_card_implemented(id),
                "Card {} ({}) not implemented",
                id,
                def.name
            );
        }
    }

    #[test]
    fn test_game_state_clone_and_determinize() {
        let cfg = GameConfig::default();
        let gs = create_initial_state(&cfg, None);
        let cloned = gs.clone();
        assert_eq!(gs.world_deck, cloned.world_deck);
        assert_eq!(gs.round_number, cloned.round_number);

        // Determinize from player 1's view: player 1's own adviser stays identical
        let mut rng = FastRng::seed_from_u64(999);
        let det = gs.determinize(1, &mut rng);
        assert_eq!(det.players[1].advisers, gs.players[1].advisers);
        assert_eq!(det.world_deck.len(), gs.world_deck.len());
    }

    #[test]
    fn test_binding_deal_and_counter_offer() {
        let cfg = GameConfig::default();
        let mut gs = create_initial_state(&cfg, None);
        gs.players[0].favor = 5;
        gs.players[1].favor = 5;
        gs.players[0].secrets_faceup = 3;
        gs.players[1].secrets_faceup = 3;

        // Chancellor offers Citizenship to Player 1 (rel=1)
        let offer_act = encode_action(Action::OfferCitizenship(1));
        assert_eq!(legal_mask(&gs)[offer_act as usize], 1);
        step(&mut gs, offer_act).unwrap();
        assert!(matches!(gs.decision, DecisionPoint::DealCompose { player: 0 }));

        // Offer +2 favor, request +1 secret, submit
        step(&mut gs, encode_action(Action::DealOfferFavorPlus)).unwrap();
        step(&mut gs, encode_action(Action::DealOfferFavorPlus)).unwrap();
        step(&mut gs, encode_action(Action::DealRequestSecretPlus)).unwrap();
        step(&mut gs, encode_action(Action::Confirm)).unwrap();

        // ReactiveTalk window for Player 1
        assert!(matches!(gs.decision, DecisionPoint::ReactiveTalk { player: 1, .. }));
        step(&mut gs, encode_action(Action::PassTalk)).unwrap();

        // Player 1 counters
        assert!(matches!(gs.decision, DecisionPoint::DealRespond { player: 1 }));
        step(&mut gs, encode_action(Action::DealCounterOffer)).unwrap();
        assert!(matches!(gs.decision, DecisionPoint::DealCompose { player: 1 }));

        // Player 1 submits counter, Player 0 passes talk and accepts
        step(&mut gs, encode_action(Action::Confirm)).unwrap();
        step(&mut gs, encode_action(Action::PassTalk)).unwrap();
        step(&mut gs, encode_action(Action::Confirm)).unwrap();

        // Player 1 is now a Citizen!
        assert_eq!(gs.players[1].role, Role::Citizen);
    }

    #[test]
    fn test_tribunal_contract_enforcement() {
        let cfg = GameConfig::default();
        let mut gs = create_initial_state(&cfg, None);
        // Place The Tribunal at site 0
        gs.sites[0].site_id = SITE_THE_TRIBUNAL;
        gs.players[0].pawn_site = 0;
        gs.players[1].pawn_site = 0;

        // Use Site Action (slot 6) -> choose Player 1
        step(&mut gs, encode_action(Action::UseCardAction(6))).unwrap();
        step(&mut gs, encode_action(Action::SelectRelPlayer(1))).unwrap();
        assert!(matches!(gs.decision, DecisionPoint::DealCompose { player: 0 }));

        // Add Non-Aggression contract (HardEnforced) and submit
        step(&mut gs, encode_action(Action::DealAddNonAggression)).unwrap();
        step(&mut gs, encode_action(Action::Confirm)).unwrap();
        step(&mut gs, encode_action(Action::PassTalk)).unwrap();
        step(&mut gs, encode_action(Action::Confirm)).unwrap();

        assert_eq!(gs.active_contracts.len(), 1);
        assert!(engine::deals::is_campaign_blocked_by_contract(&gs, 1, 0));
    }

    #[test]
    fn test_table_talk_and_mechanical_show_adviser() {
        let cfg = GameConfig::default();
        let mut gs = create_initial_state(&cfg, None);
        assert!(!gs.knowledge[1].knows_adviser(0, 0));

        // Player 0 shows facedown adviser slot 0
        step(&mut gs, encode_action(Action::TalkShowAdviser(0))).unwrap();
        assert!(gs.knowledge[1].knows_adviser(0, 0));
        assert_eq!(gs.talk_log.len(), 1);

        // Observation for player 1 now reveals player 0's adviser 0
        let obs1 = encode_observation(&gs, 1);
        let p0_rel = (0 + 4 - 1) % 4; // rel index of player 0 from player 1's view = 3
        assert_eq!(obs1.card_ids[32 + p0_rel * 3], gs.players[0].advisers[0] as i32);
    }

    #[test]
    fn test_fuzz_200_random_and_heuristic_games_no_deadlocks() {
        for seed in 0..100u64 {
            let cfg = GameConfig {
                num_players: (2 + (seed % 5)) as u8,
                seed,
                first_game: seed % 2 == 0,
                oath_goal: Some(OathGoal::ALL[(seed % 4) as usize]),
                chronicle_enabled: seed % 5 == 0,
            };
            let mut gs = create_initial_state(&cfg, None);
            let mut rng = FastRng::seed_from_u64(seed.wrapping_mul(31337));
            let mut steps = 0;
            while !gs.is_game_over && steps < 6000 {
                let mask = legal_mask(&gs);
                assert!(
                    mask.iter().any(|&m| m != 0),
                    "Deadlock at seed={}, step={}, decision={:?}",
                    seed,
                    steps,
                    gs.decision
                );
                let act = if seed % 2 == 0 {
                    random_agent_action(&gs, &mut rng)
                } else {
                    heuristic_agent_action(&gs, &mut rng)
                };
                step(&mut gs, act).unwrap();
                steps += 1;
            }
            assert!(gs.is_game_over, "Game did not terminate for seed={}", seed);
            assert!(gs.winner.is_some());

            if cfg.chronicle_enabled {
                let ch = apply_chronicle(&mut gs);
                let next_gs = create_initial_state(&cfg, Some(&ch));
                assert_eq!(next_gs.round_number, 1);
            }
        }
    }

    #[test]
    fn test_vec_env_parallel_rollouts() {
        let mut vec_env = VecOathEnv::new(8, 4, 1234, Some(1), false);
        let mut rng = FastRng::seed_from_u64(42);
        let init = vec_env.observe_all();
        assert_eq!(init.obs_flat.len(), 8 * OBS_FLAT_SIZE);
        for _ in 0..50 {
            let actions: Vec<ActionId> = (0..8)
                .map(|i| random_agent_action(&vec_env.envs[i], &mut rng))
                .collect();
            let out = vec_env.step_all(&actions);
            assert_eq!(out.rewards.len(), 8);
        }
    }
}

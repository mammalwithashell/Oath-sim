use rayon::prelude::*;

use crate::actions::NUM_ACTIONS;
use crate::agents::{heuristic_agent_action, random_agent_action};
use crate::engine::{
    self,
    chronicle::apply_chronicle,
    setup::{create_initial_state, GameConfig},
};
use crate::obs::{encode_observation, OBS_CARD_IDS_SIZE, OBS_FLAT_SIZE};
use crate::rng::FastRng;
use crate::state::{ChronicleState, GameState};
use crate::types::*;

/// Opponent policy for non-RL seats in single-agent mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum OpponentMode {
    DeterministicBot = 0,
    Random = 1,
}

/// High-throughput Rayon-parallel vectorized Oath environment.
/// Supports:
/// - Full 4-player self-play (`single_agent_player = None`)
/// - Single-agent training against Deterministic Role-Aware Bots or Random opponents
/// - Unlimited or bounded long-lineage Chronicle mode (`chronicle_enabled = true`)
pub struct VecOathEnv {
    pub envs: Vec<GameState>,
    pub configs: Vec<GameConfig>,
    pub chronicles: Vec<Option<ChronicleState>>,
    pub chronicle_games: Vec<u32>,
    pub chronicle_max_length: u32, // 0 = unlimited continuous chronicle!
    pub single_agent_player: Option<PlayerId>,
    pub opponent_mode: OpponentMode,
    pub agent_rngs: Vec<FastRng>,
}

pub struct VecStepOutput {
    pub obs_flat: Vec<f32>,
    pub card_ids: Vec<i32>,
    pub action_masks: Vec<i8>,
    pub rewards: Vec<f32>,
    pub dones: Vec<bool>,
    pub acting_players: Vec<u8>,
    pub winners: Vec<i8>, // -1 if not done, else winner PlayerId
}

impl VecOathEnv {
    pub fn new(
        num_envs: usize,
        num_players: u8,
        base_seed: u64,
        single_agent_player: Option<PlayerId>,
        first_game: bool,
    ) -> Self {
        Self::new_with_options(
            num_envs,
            num_players,
            base_seed,
            single_agent_player,
            first_game,
            false,
            0,
            OpponentMode::DeterministicBot,
        )
    }

    #[allow(clippy::too_many_arguments)]
    pub fn new_with_options(
        num_envs: usize,
        num_players: u8,
        base_seed: u64,
        single_agent_player: Option<PlayerId>,
        first_game: bool,
        chronicle_enabled: bool,
        chronicle_max_length: u32,
        opponent_mode: OpponentMode,
    ) -> Self {
        let mut envs = Vec::with_capacity(num_envs);
        let mut configs = Vec::with_capacity(num_envs);
        let mut chronicles = Vec::with_capacity(num_envs);
        let mut chronicle_games = Vec::with_capacity(num_envs);
        let mut agent_rngs = Vec::with_capacity(num_envs);

        for i in 0..num_envs {
            let seed = base_seed.wrapping_add((i as u64).wrapping_mul(1_000_003));
            let cfg = GameConfig {
                num_players,
                seed,
                first_game,
                oath_goal: Some(OathGoal::ALL[i % 4]),
                chronicle_enabled,
            };
            let mut gs = create_initial_state(&cfg, None);
            let mut arng = FastRng::seed_from_u64(seed ^ 0x55AA_55AA);
            if let Some(rl_p) = single_agent_player {
                advance_until_player(&mut gs, rl_p, opponent_mode, &mut arng);
            }
            envs.push(gs);
            configs.push(cfg);
            chronicles.push(None);
            chronicle_games.push(0);
            agent_rngs.push(arng);
        }

        Self {
            envs,
            configs,
            chronicles,
            chronicle_games,
            chronicle_max_length,
            single_agent_player,
            opponent_mode,
            agent_rngs,
        }
    }

    pub fn observe_all(&self) -> VecStepOutput {
        let n = self.envs.len();
        let mut obs_flat = vec![0.0f32; n * OBS_FLAT_SIZE];
        let mut card_ids = vec![0i32; n * OBS_CARD_IDS_SIZE];
        let mut action_masks = vec![0i8; n * NUM_ACTIONS];
        let mut acting_players = vec![0u8; n];
        let rewards = vec![0.0f32; n];
        let dones = vec![false; n];

        obs_flat
            .par_chunks_mut(OBS_FLAT_SIZE)
            .zip(card_ids.par_chunks_mut(OBS_CARD_IDS_SIZE))
            .zip(action_masks.par_chunks_mut(NUM_ACTIONS))
            .zip(acting_players.par_iter_mut())
            .enumerate()
            .for_each(|(i, (((of, ci), am), ap))| {
                let gs = &self.envs[i];
                let observer = self
                    .single_agent_player
                    .or_else(|| gs.decision.acting_player())
                    .unwrap_or(0);
                let obs = encode_observation(gs, observer);
                of.copy_from_slice(&obs.obs_flat);
                ci.copy_from_slice(&obs.card_ids);
                am.copy_from_slice(&obs.action_mask);
                *ap = obs.acting_player;
            });

        VecStepOutput {
            obs_flat,
            card_ids,
            action_masks,
            rewards,
            dones,
            acting_players,
            winners: vec![-1i8; n],
        }
    }

    pub fn step_all(&mut self, actions: &[ActionId]) -> VecStepOutput {
        let n = self.envs.len();
        assert_eq!(actions.len(), n);

        let mut obs_flat = vec![0.0f32; n * OBS_FLAT_SIZE];
        let mut card_ids = vec![0i32; n * OBS_CARD_IDS_SIZE];
        let mut action_masks = vec![0i8; n * NUM_ACTIONS];
        let mut rewards = vec![0.0f32; n];
        let mut dones = vec![false; n];
        let mut acting_players = vec![0u8; n];
        let mut winners = vec![-1i8; n];
        let single_p = self.single_agent_player;
        let opp_mode = self.opponent_mode;
        let ch_max = self.chronicle_max_length;

        self.envs
            .par_iter_mut()
            .zip(self.configs.par_iter_mut())
            .zip(self.chronicles.par_iter_mut())
            .zip(self.chronicle_games.par_iter_mut())
            .zip(self.agent_rngs.par_iter_mut())
            .zip(obs_flat.par_chunks_mut(OBS_FLAT_SIZE))
            .zip(card_ids.par_chunks_mut(OBS_CARD_IDS_SIZE))
            .zip(action_masks.par_chunks_mut(NUM_ACTIONS))
            .zip(rewards.par_iter_mut())
            .zip(dones.par_iter_mut())
            .zip(acting_players.par_iter_mut())
            .zip(winners.par_iter_mut())
            .enumerate()
            .for_each(
                |(i, (((((((((((gs, cfg), ch), ch_cnt), arng), of), ci), am), rew), done), ap), win_out))| {
                    let actor = gs.decision.acting_player().unwrap_or(0);
                    let eval_p = single_p.unwrap_or(actor);
                    let prev_sites = gs.count_sites_ruled(eval_p);
                    let prev_rb = gs.count_relics_and_banners(eval_p);
                    let prev_ok = gs.oathkeeper_holder == Some(eval_p);
                    let prev_usurper = prev_ok && gs.oathkeeper_side == TitleSide::Usurper;
                    let prev_vis = gs.players[eval_p as usize].revealed_vision.is_some();

                    let _ = engine::step(gs, actions[i]);

                    if let Some(rl_p) = single_p {
                        advance_until_player(gs, rl_p, opp_mode, arng);
                    }

                    if gs.is_game_over {
                        *done = true;
                        *win_out = gs.winner.map(|w| w as i8).unwrap_or(-1);
                        *rew = if gs.winner == Some(eval_p) { 1.0 } else { -1.0 };
                        cfg.seed = cfg.seed.wrapping_add(7919);

                        if cfg.chronicle_enabled {
                            *ch_cnt += 1;
                            if ch_max > 0 && *ch_cnt >= ch_max {
                                *ch = None;
                                *ch_cnt = 0;
                            } else {
                                *ch = Some(apply_chronicle(gs));
                            }
                        } else {
                            *ch = None;
                        }

                        *gs = create_initial_state(cfg, ch.as_ref());
                        if let Some(rl_p) = single_p {
                            advance_until_player(gs, rl_p, opp_mode, arng);
                        }
                    } else {
                        let new_sites = gs.count_sites_ruled(eval_p);
                        let new_rb = gs.count_relics_and_banners(eval_p);
                        let new_ok = gs.oathkeeper_holder == Some(eval_p);
                        let new_usurper = new_ok && gs.oathkeeper_side == TitleSide::Usurper;
                        let new_vis = gs.players[eval_p as usize].revealed_vision.is_some();

                        let mut r = 0.0f32;
                        r += (new_sites as i8 - prev_sites as i8) as f32 * 0.02;
                        r += (new_rb as i8 - prev_rb as i8) as f32 * 0.04;
                        if new_ok && !prev_ok {
                            r += 0.08;
                        } else if !new_ok && prev_ok {
                            r -= 0.05;
                        }
                        if new_usurper && !prev_usurper {
                            r += 0.15;
                        }
                        if new_vis && !prev_vis {
                            r += 0.05;
                        }
                        *rew = r;
                    }

                    let observer = single_p
                        .or_else(|| gs.decision.acting_player())
                        .unwrap_or(0);
                    let obs = encode_observation(gs, observer);
                    of.copy_from_slice(&obs.obs_flat);
                    ci.copy_from_slice(&obs.card_ids);
                    am.copy_from_slice(&obs.action_mask);
                    *ap = obs.acting_player;
                },
            );

        VecStepOutput {
            obs_flat,
            card_ids,
            action_masks,
            rewards,
            dones,
            acting_players,
            winners,
        }
    }
}

fn advance_until_player(
    gs: &mut GameState,
    target: PlayerId,
    opponent_mode: OpponentMode,
    rng: &mut FastRng,
) {
    let mut guard = 0;
    while !gs.is_game_over && guard < 1500 {
        if gs.decision.acting_player() == Some(target) {
            break;
        }
        let act = match opponent_mode {
            OpponentMode::DeterministicBot => heuristic_agent_action(gs, rng),
            OpponentMode::Random => random_agent_action(gs, rng),
        };
        if engine::step(gs, act).is_err() {
            break;
        }
        guard += 1;
    }
}

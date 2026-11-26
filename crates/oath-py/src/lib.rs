use numpy::{IntoPyArray, PyArray1, PyArray2, PyArrayMethods, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use oath_core::agents::{heuristic_agent_action, random_agent_action};
use oath_core::{
    apply_chronicle, create_initial_state, describe_action, encode_observation, get_card,
    legal_mask, step as core_step, ActionId, ChronicleState, FastRng, GameConfig, GameState,
    OathGoal, PlayerId, VecOathEnv, NUM_ACTIONS, NUM_CARDS, OBS_CARD_IDS_SIZE, OBS_FLAT_SIZE,
};

#[pyclass(name = "OathEnv")]
#[derive(Clone)]
pub struct PyOathEnv {
    gs: GameState,
    config: GameConfig,
    chronicle: Option<ChronicleState>,
}

#[pymethods]
impl PyOathEnv {
    #[new]
    #[pyo3(signature = (num_players=4, seed=42, first_game=true, oath_goal=None, chronicle_enabled=false))]
    fn new(
        num_players: u8,
        seed: u64,
        first_game: bool,
        oath_goal: Option<u8>,
        chronicle_enabled: bool,
    ) -> Self {
        let cfg = GameConfig {
            num_players,
            seed,
            first_game,
            oath_goal: oath_goal.and_then(OathGoal::from_u8),
            chronicle_enabled,
        };
        let gs = create_initial_state(&cfg, None);
        Self {
            gs,
            config: cfg,
            chronicle: None,
        }
    }

    #[pyo3(signature = (seed=None, oath_goal=None))]
    fn reset(&mut self, seed: Option<u64>, oath_goal: Option<u8>) {
        if let Some(s) = seed {
            self.config.seed = s;
        } else {
            self.config.seed = self.config.seed.wrapping_add(7919);
        }
        if let Some(og) = oath_goal {
            self.config.oath_goal = OathGoal::from_u8(og);
        }
        if self.config.chronicle_enabled && self.gs.is_game_over {
            self.chronicle = Some(apply_chronicle(&mut self.gs));
        }
        self.gs = create_initial_state(&self.config, self.chronicle.as_ref());
    }

    fn step<'py>(
        &mut self,
        py: Python<'py>,
        action_id: ActionId,
    ) -> PyResult<(
        Bound<'py, PyArray1<f32>>,
        Bound<'py, PyArray1<i32>>,
        Bound<'py, PyArray1<i8>>,
        u8,
        bool,
        Option<u8>,
    )> {
        core_step(&mut self.gs, action_id).map_err(|e| PyValueError::new_err(e))?;
        let acting = self.gs.decision.acting_player().unwrap_or(0);
        let obs = encode_observation(&self.gs, acting);
        Ok((
            obs.obs_flat.to_vec().into_pyarray_bound(py),
            obs.card_ids.to_vec().into_pyarray_bound(py),
            obs.action_mask.to_vec().into_pyarray_bound(py),
            acting,
            self.gs.is_game_over,
            self.gs.winner,
        ))
    }

    #[pyo3(signature = (observer=None))]
    fn observe<'py>(
        &self,
        py: Python<'py>,
        observer: Option<PlayerId>,
    ) -> (
        Bound<'py, PyArray1<f32>>,
        Bound<'py, PyArray1<i32>>,
        Bound<'py, PyArray1<i8>>,
        u8,
    ) {
        let obs_p = observer
            .or_else(|| self.gs.decision.acting_player())
            .unwrap_or(0);
        let obs = encode_observation(&self.gs, obs_p);
        (
            obs.obs_flat.to_vec().into_pyarray_bound(py),
            obs.card_ids.to_vec().into_pyarray_bound(py),
            obs.action_mask.to_vec().into_pyarray_bound(py),
            obs.acting_player,
        )
    }

    /// Exact fast Rust state clone for AlphaZero / MCTS tree search.
    fn clone_env(&self) -> Self {
        self.clone()
    }

    /// Determinize hidden information from `observer`'s perspective for IS-MCTS.
    fn determinize(&self, observer: PlayerId, seed: u64) -> Self {
        let mut rng = FastRng::seed_from_u64(seed);
        let det = self.gs.determinize(observer, &mut rng);
        Self {
            gs: det,
            config: self.config.clone(),
            chronicle: self.chronicle.clone(),
        }
    }

    fn acting_player(&self) -> Option<u8> {
        self.gs.decision.acting_player()
    }

    fn is_game_over(&self) -> bool {
        self.gs.is_game_over
    }

    fn winner(&self) -> Option<u8> {
        self.gs.winner
    }

    fn round_number(&self) -> u8 {
        self.gs.round_number
    }

    fn num_players(&self) -> u8 {
        self.gs.num_players
    }

    fn legal_actions_described(&self) -> Vec<(ActionId, String)> {
        let mask = legal_mask(&self.gs);
        let mut out = Vec::new();
        for (i, &m) in mask.iter().enumerate() {
            if m != 0 {
                let id = i as ActionId;
                out.push((id, describe_action(&self.gs, id)));
            }
        }
        out
    }

    fn heuristic_action(&self, seed: u64) -> ActionId {
        let mut rng = FastRng::seed_from_u64(seed);
        heuristic_agent_action(&self.gs, &mut rng)
    }

    fn random_action(&self, seed: u64) -> ActionId {
        let mut rng = FastRng::seed_from_u64(seed);
        random_agent_action(&self.gs, &mut rng)
    }

    fn state_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.gs).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Replace the live GameState from an exact serialized JSON snapshot (e.g. replay takeover).
    fn load_state_json(&mut self, state_json: &str) -> PyResult<()> {
        let gs: GameState =
            serde_json::from_str(state_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        self.config.num_players = gs.num_players;
        self.gs = gs;
        Ok(())
    }

    /// Export the current ChronicleState as JSON (computes it from the finished game if needed).
    fn export_chronicle_json(&mut self) -> PyResult<String> {
        let ch = if self.gs.is_game_over {
            let applied = apply_chronicle(&mut self.gs);
            self.chronicle = Some(applied.clone());
            applied
        } else if let Some(ref existing) = self.chronicle {
            existing.clone()
        } else {
            // Snapshot current live state into a ChronicleState even mid-game
            apply_chronicle(&mut self.gs.clone())
        };
        serde_json::to_string_pretty(&ch).map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Import a ChronicleState JSON and initialize a fresh game from it.
    #[pyo3(signature = (chronicle_json, seed=None))]
    fn import_chronicle_json(&mut self, chronicle_json: &str, seed: Option<u64>) -> PyResult<()> {
        let ch: ChronicleState = serde_json::from_str(chronicle_json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        if let Some(s) = seed {
            self.config.seed = s;
        }
        self.config.chronicle_enabled = true;
        self.gs = create_initial_state(&self.config, Some(&ch));
        self.chronicle = Some(ch);
        Ok(())
    }

    /// Stage custom map sites (up to 8 site CardIds 237..259), Reliquary relics (up to 4, 211..230),
    /// Chancellor held relics (211..230), and/or starting Oath Goal (0..3).
    #[pyo3(signature = (sites=None, reliquary=None, chancellor_relics=None, oath_goal=None))]
    fn stage_scenario(
        &mut self,
        sites: Option<Vec<u16>>,
        reliquary: Option<Vec<u16>>,
        chancellor_relics: Option<Vec<u16>>,
        oath_goal: Option<u8>,
    ) -> PyResult<()> {
        if let Some(og) = oath_goal.and_then(OathGoal::from_u8) {
            self.gs.oath_goal = og;
            self.gs.successor_goal = og.successor_goal();
            self.config.oath_goal = Some(og);
            self.gs.peoples_favor_holder = if og == OathGoal::People { Some(0) } else { None };
            self.gs.darkest_secret_holder = if og == OathGoal::Devotion { Some(0) } else { None };
        }
        if let Some(site_ids) = sites {
            for (idx, sid) in site_ids.into_iter().take(8).enumerate() {
                if (237..=259).contains(&sid) {
                    let def = get_card(sid);
                    self.gs.sites[idx].site_id = sid;
                    self.gs.sites[idx].capacity = def.capacity;
                }
            }
        }
        if let Some(rel_ids) = reliquary {
            self.gs.reliquary.clear();
            for rid in rel_ids.into_iter().take(4) {
                if (211..=230).contains(&rid) {
                    self.gs.relic_deck.retain(|&r| r != rid);
                    self.gs.reliquary.push(rid);
                }
            }
        }
        if let Some(ch_rels) = chancellor_relics {
            self.gs.players[0].relics.clear();
            self.gs.players[0].relics.push(oath_core::CARD_GRAND_SCEPTER);
            for rid in ch_rels.into_iter().take(5) {
                if (211..=230).contains(&rid) && !self.gs.players[0].relics.contains(&rid) {
                    self.gs.relic_deck.retain(|&r| r != rid);
                    self.gs.reliquary.retain(|r| *r != rid);
                    self.gs.players[0].relics.push(rid);
                }
            }
        }
        Ok(())
    }

    /// Run parallel Determinized IS-MCTS (AlphaZero PUCT) in native Rust.
    /// Returns (best_action, policy_array[216], root_values[6]).
    #[pyo3(signature = (num_determinizations=4, sims_per_det=64, c_puct=1.4, max_rollout_steps=200, seed=42, root_prior=None))]
    fn mcts_search<'py>(
        &self,
        py: Python<'py>,
        num_determinizations: usize,
        sims_per_det: usize,
        c_puct: f32,
        max_rollout_steps: usize,
        seed: u64,
        root_prior: Option<PyReadonlyArray1<'py, f32>>,
    ) -> PyResult<(ActionId, Bound<'py, PyArray1<f32>>, Bound<'py, PyArray1<f32>>)> {
        let prior_arr: Option<[f32; NUM_ACTIONS]> = if let Some(rp) = root_prior {
            let sl = rp.as_slice()?;
            if sl.len() != NUM_ACTIONS {
                return Err(PyValueError::new_err("root_prior must have length NUM_ACTIONS"));
            }
            let mut arr = [0.0f32; NUM_ACTIONS];
            arr.copy_from_slice(sl);
            Some(arr)
        } else {
            None
        };
        let observer = self.gs.decision.acting_player().unwrap_or(0);
        let cfg = oath_mcts::MctsConfig {
            num_determinizations,
            sims_per_det,
            c_puct,
            max_rollout_steps,
            seed,
        };
        let res = py.allow_threads(|| {
            oath_mcts::search_ismcts(&self.gs, observer, &cfg, prior_arr.as_ref())
        });
        Ok((
            res.best_action,
            res.policy.to_vec().into_pyarray_bound(py),
            res.root_values.to_vec().into_pyarray_bound(py),
        ))
    }
}

#[pyclass(name = "VecOathEnv")]
pub struct PyVecOathEnv {
    inner: VecOathEnv,
    num_envs: usize,
}

#[pymethods]
impl PyVecOathEnv {
    #[new]
    #[pyo3(signature = (num_envs=32, num_players=4, base_seed=42, single_agent_player=Some(1), first_game=false, chronicle_enabled=false, chronicle_max_length=0, opponent_mode="bot"))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        num_envs: usize,
        num_players: u8,
        base_seed: u64,
        single_agent_player: Option<PlayerId>,
        first_game: bool,
        chronicle_enabled: bool,
        chronicle_max_length: u32,
        opponent_mode: &str,
    ) -> Self {
        let mode = match opponent_mode {
            "random" => oath_core::vec_env::OpponentMode::Random,
            _ => oath_core::vec_env::OpponentMode::DeterministicBot,
        };
        Self {
            inner: VecOathEnv::new_with_options(
                num_envs,
                num_players,
                base_seed,
                single_agent_player,
                first_game,
                chronicle_enabled,
                chronicle_max_length,
                mode,
            ),
            num_envs,
        }
    }

    fn observe_all<'py>(
        &self,
        py: Python<'py>,
    ) -> PyResult<(
        Bound<'py, PyArray2<f32>>,
        Bound<'py, PyArray2<i32>>,
        Bound<'py, PyArray2<i8>>,
        Bound<'py, PyArray1<u8>>,
    )> {
        let out = py.allow_threads(|| self.inner.observe_all());
        let of = out
            .obs_flat
            .into_pyarray_bound(py)
            .reshape([self.num_envs, OBS_FLAT_SIZE])?;
        let ci = out
            .card_ids
            .into_pyarray_bound(py)
            .reshape([self.num_envs, OBS_CARD_IDS_SIZE])?;
        let am = out
            .action_masks
            .into_pyarray_bound(py)
            .reshape([self.num_envs, NUM_ACTIONS])?;
        let ap = out.acting_players.into_pyarray_bound(py);
        Ok((of, ci, am, ap))
    }

    fn step_all<'py>(
        &mut self,
        py: Python<'py>,
        actions: PyReadonlyArray1<'py, u16>,
    ) -> PyResult<(
        Bound<'py, PyArray2<f32>>,
        Bound<'py, PyArray2<i32>>,
        Bound<'py, PyArray2<i8>>,
        Bound<'py, PyArray1<f32>>,
        Bound<'py, PyArray1<bool>>,
        Bound<'py, PyArray1<u8>>,
        Bound<'py, PyArray1<i8>>,
    )> {
        let act_slice = actions.as_slice()?;
        if act_slice.len() != self.num_envs {
            return Err(PyValueError::new_err("actions length must match num_envs"));
        }
        let out = py.allow_threads(|| self.inner.step_all(act_slice));
        let of = out
            .obs_flat
            .into_pyarray_bound(py)
            .reshape([self.num_envs, OBS_FLAT_SIZE])?;
        let ci = out
            .card_ids
            .into_pyarray_bound(py)
            .reshape([self.num_envs, OBS_CARD_IDS_SIZE])?;
        let am = out
            .action_masks
            .into_pyarray_bound(py)
            .reshape([self.num_envs, NUM_ACTIONS])?;
        let rw = out.rewards.into_pyarray_bound(py);
        let dn = out.dones.into_pyarray_bound(py);
        let ap = out.acting_players.into_pyarray_bound(py);
        let wn = out.winners.into_pyarray_bound(py);
        Ok((of, ci, am, rw, dn, ap, wn))
    }
}

/// Fast native-Rust dataset collector for Behavioral Cloning warm-start from Role-Aware Bots.
#[pyfunction]
#[pyo3(signature = (num_samples=40000, num_players=4, seed=1234, chronicle_enabled=true))]
fn collect_bot_dataset<'py>(
    py: Python<'py>,
    num_samples: usize,
    num_players: u8,
    seed: u64,
    chronicle_enabled: bool,
) -> PyResult<(
    Bound<'py, PyArray2<f32>>,
    Bound<'py, PyArray2<i32>>,
    Bound<'py, PyArray2<i8>>,
    Bound<'py, PyArray1<u16>>,
)> {
    let (obs_buf, cid_buf, mask_buf, act_buf) = py.allow_threads(|| {
        let mut obs_buf = Vec::with_capacity(num_samples * OBS_FLAT_SIZE);
        let mut cid_buf = Vec::with_capacity(num_samples * OBS_CARD_IDS_SIZE);
        let mut mask_buf = Vec::with_capacity(num_samples * NUM_ACTIONS);
        let mut act_buf = Vec::with_capacity(num_samples);

        let mut cfg = GameConfig {
            num_players,
            seed,
            first_game: false,
            oath_goal: Some(OathGoal::Supremacy),
            chronicle_enabled,
        };
        let mut ch: Option<ChronicleState> = None;
        let mut gs = create_initial_state(&cfg, None);
        let mut rng = FastRng::seed_from_u64(seed ^ 0xCAFE_BABE);
        let mut game_idx = 0usize;

        while act_buf.len() < num_samples {
            if gs.is_game_over {
                game_idx += 1;
                cfg.seed = cfg.seed.wrapping_add(7919);
                if chronicle_enabled && game_idx % 20 != 0 {
                    ch = Some(apply_chronicle(&mut gs));
                } else {
                    ch = None;
                    cfg.oath_goal = Some(OathGoal::ALL[game_idx % 4]);
                }
                gs = create_initial_state(&cfg, ch.as_ref());
            }
            let acting = gs.decision.acting_player().unwrap_or(0);
            let obs = encode_observation(&gs, acting);
            let act = heuristic_agent_action(&gs, &mut rng);
            obs_buf.extend_from_slice(&obs.obs_flat);
            cid_buf.extend_from_slice(&obs.card_ids);
            mask_buf.extend_from_slice(&obs.action_mask);
            act_buf.push(act);
            let _ = core_step(&mut gs, act);
        }
        (obs_buf, cid_buf, mask_buf, act_buf)
    });

    let of = obs_buf
        .into_pyarray_bound(py)
        .reshape([num_samples, OBS_FLAT_SIZE])?;
    let ci = cid_buf
        .into_pyarray_bound(py)
        .reshape([num_samples, OBS_CARD_IDS_SIZE])?;
    let am = mask_buf
        .into_pyarray_bound(py)
        .reshape([num_samples, NUM_ACTIONS])?;
    let ac = act_buf.into_pyarray_bound(py);
    Ok((of, ci, am, ac))
}

#[pyfunction]
fn card_info(card_id: u16) -> (u16, &'static str, &'static str, &'static str) {
    let c = get_card(card_id);
    let suit = c.suit.map(|s| s.name()).unwrap_or("None");
    (c.id, c.name, suit, c.effect_text)
}

#[pymodule]
fn oath_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyOathEnv>()?;
    m.add_class::<PyVecOathEnv>()?;
    m.add_function(wrap_pyfunction!(card_info, m)?)?;
    m.add_function(wrap_pyfunction!(collect_bot_dataset, m)?)?;
    m.add("NUM_ACTIONS", NUM_ACTIONS)?;
    m.add("OBS_FLAT_SIZE", OBS_FLAT_SIZE)?;
    m.add("OBS_CARD_IDS_SIZE", OBS_CARD_IDS_SIZE)?;
    m.add("NUM_CARDS", NUM_CARDS)?;
    Ok(())
}

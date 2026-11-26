use rayon::prelude::*;

use oath_core::agents::heuristic_agent_action;
use oath_core::{
    legal_mask, step, ActionId, FastRng, GameState, PlayerId, MAX_PLAYERS, NUM_ACTIONS,
};

#[derive(Debug, Clone)]
pub struct MctsConfig {
    /// Number of determinized worlds sampled at the root (IS-MCTS)
    pub num_determinizations: usize,
    /// MCTS simulations per determinization
    pub sims_per_det: usize,
    /// PUCT exploration constant
    pub c_puct: f32,
    /// Max rollout depth for default value evaluation
    pub max_rollout_steps: usize,
    pub seed: u64,
}

impl Default for MctsConfig {
    fn default() -> Self {
        Self {
            num_determinizations: 4,
            sims_per_det: 64,
            c_puct: 1.4,
            max_rollout_steps: 250,
            seed: 42,
        }
    }
}

#[derive(Debug, Clone)]
pub struct MctsResult {
    pub best_action: ActionId,
    pub visit_counts: [u32; NUM_ACTIONS],
    pub policy: [f32; NUM_ACTIONS],
    pub root_values: [f32; MAX_PLAYERS],
}

struct Node {
    acting_player: PlayerId,
    is_terminal: bool,
    terminal_values: [f32; MAX_PLAYERS],
    visits: u32,
    /// Edge actions, priors, visits, value_sum (for each player)
    actions: Vec<ActionId>,
    priors: Vec<f32>,
    edge_visits: Vec<u32>,
    edge_value_sums: Vec<[f32; MAX_PLAYERS]>,
    children: Vec<Option<usize>>,
}

impl Node {
    fn new(gs: &GameState, uniform_priors: Option<&[f32; NUM_ACTIONS]>) -> Self {
        let acting_player = gs.decision.acting_player().unwrap_or(0);
        if gs.is_game_over {
            let mut tv = [0.0f32; MAX_PLAYERS];
            if let Some(w) = gs.winner {
                tv[w as usize] = 1.0;
            }
            return Self {
                acting_player,
                is_terminal: true,
                terminal_values: tv,
                visits: 0,
                actions: Vec::new(),
                priors: Vec::new(),
                edge_visits: Vec::new(),
                edge_value_sums: Vec::new(),
                children: Vec::new(),
            };
        }

        let mask = legal_mask(gs);
        let mut actions = Vec::new();
        let mut priors = Vec::new();
        let mut sum_p = 0.0f32;
        for (i, &m) in mask.iter().enumerate() {
            if m != 0 {
                actions.push(i as ActionId);
                let p = uniform_priors.map(|pr| pr[i].max(1e-6)).unwrap_or(1.0);
                priors.push(p);
                sum_p += p;
            }
        }
        if sum_p > 0.0 {
            for p in &mut priors {
                *p /= sum_p;
            }
        }
        let len = actions.len();
        Self {
            acting_player,
            is_terminal: false,
            terminal_values: [0.0; MAX_PLAYERS],
            visits: 0,
            actions,
            priors,
            edge_visits: vec![0; len],
            edge_value_sums: vec![[0.0; MAX_PLAYERS]; len],
            children: vec![None; len],
        }
    }
}

/// Run parallel Determinized IS-MCTS (AlphaZero PUCT) from `observer`'s perspective.
/// Accepts optional root policy prior (e.g. from PyTorch neural network) and uses
/// fast native Rust cloning + multi-player value vectors `[f32; MAX_PLAYERS]`.
pub fn search_ismcts(
    root_state: &GameState,
    observer: PlayerId,
    config: &MctsConfig,
    root_prior: Option<&[f32; NUM_ACTIONS]>,
) -> MctsResult {
    let det_results: Vec<([u32; NUM_ACTIONS], [f32; MAX_PLAYERS])> = (0..config.num_determinizations)
        .into_par_iter()
        .map(|d| {
            let mut rng = FastRng::seed_from_u64(
                config
                    .seed
                    .wrapping_add((d as u64).wrapping_mul(0x9E37_79B9)),
            );
            let det_state = root_state.determinize(observer, &mut rng);
            run_single_tree(&det_state, config, root_prior, &mut rng)
        })
        .collect();

    let mut total_visits = [0u32; NUM_ACTIONS];
    let mut total_vals = [0.0f32; MAX_PLAYERS];
    for (vc, rv) in det_results {
        for i in 0..NUM_ACTIONS {
            total_visits[i] += vc[i];
        }
        for p in 0..MAX_PLAYERS {
            total_vals[p] += rv[p];
        }
    }
    let denom = config.num_determinizations.max(1) as f32;
    for v in &mut total_vals {
        *v /= denom;
    }

    let sum_v: u32 = total_visits.iter().sum();
    let mut policy = [0.0f32; NUM_ACTIONS];
    let mut best_action = 0 as ActionId;
    let mut best_cnt = 0u32;
    if sum_v > 0 {
        for i in 0..NUM_ACTIONS {
            policy[i] = total_visits[i] as f32 / sum_v as f32;
            if total_visits[i] > best_cnt {
                best_cnt = total_visits[i];
                best_action = i as ActionId;
            }
        }
    } else {
        // Fallback to first legal action
        let mask = legal_mask(root_state);
        for (i, &m) in mask.iter().enumerate() {
            if m != 0 {
                best_action = i as ActionId;
                policy[i] = 1.0;
                break;
            }
        }
    }

    MctsResult {
        best_action,
        visit_counts: total_visits,
        policy,
        root_values: total_vals,
    }
}

fn run_single_tree(
    root_state: &GameState,
    config: &MctsConfig,
    root_prior: Option<&[f32; NUM_ACTIONS]>,
    rng: &mut FastRng,
) -> ([u32; NUM_ACTIONS], [f32; MAX_PLAYERS]) {
    let mut arena: Vec<Node> = Vec::with_capacity(config.sims_per_det + 1);
    arena.push(Node::new(root_state, root_prior));

    for _ in 0..config.sims_per_det {
        let mut gs = root_state.clone();
        // Re-seed per simulation so chance nodes (dice rolls) sample independently
        gs.rng = FastRng::seed_from_u64(rng.next_u64_fast());

        let mut path: Vec<(usize, usize)> = Vec::new();
        let mut node_idx = 0usize;

        // Selection
        loop {
            let node = &arena[node_idx];
            if node.is_terminal || node.actions.is_empty() {
                break;
            }
            let acting = node.acting_player as usize;
            let sqrt_n = ((node.visits.max(1)) as f32).sqrt();
            let mut best_edge = 0usize;
            let mut best_score = f32::NEG_INFINITY;

            for e in 0..node.actions.len() {
                let ev = node.edge_visits[e];
                let q = if ev > 0 {
                    node.edge_value_sums[e][acting] / ev as f32
                } else {
                    0.25
                };
                let u = config.c_puct * node.priors[e] * sqrt_n / (1.0 + ev as f32);
                let score = q + u;
                if score > best_score {
                    best_score = score;
                    best_edge = e;
                }
            }

            let act = node.actions[best_edge];
            path.push((node_idx, best_edge));
            let _ = step(&mut gs, act);

            if let Some(child) = arena[node_idx].children[best_edge] {
                node_idx = child;
            } else {
                // Expansion
                let new_idx = arena.len();
                arena.push(Node::new(&gs, None));
                arena[node_idx].children[best_edge] = Some(new_idx);
                node_idx = new_idx;
                break;
            }
        }

        // Evaluation (fast heuristic rollout to terminal or horizon)
        let values = if arena[node_idx].is_terminal {
            arena[node_idx].terminal_values
        } else {
            evaluate_rollout(&mut gs, config.max_rollout_steps, rng)
        };

        // Backpropagation
        arena[node_idx].visits += 1;
        for &(ni, edge) in path.iter().rev() {
            arena[ni].visits += 1;
            arena[ni].edge_visits[edge] += 1;
            for p in 0..MAX_PLAYERS {
                arena[ni].edge_value_sums[edge][p] += values[p];
            }
        }
    }

    let mut vc = [0u32; NUM_ACTIONS];
    let mut rv = [0.0f32; MAX_PLAYERS];
    let root = &arena[0];
    let mut sum_v = 0u32;
    for (e, &act) in root.actions.iter().enumerate() {
        let ev = root.edge_visits[e];
        vc[act as usize] = ev;
        sum_v += ev;
        for p in 0..MAX_PLAYERS {
            rv[p] += root.edge_value_sums[e][p];
        }
    }
    if sum_v > 0 {
        for p in 0..MAX_PLAYERS {
            rv[p] /= sum_v as f32;
        }
    }
    (vc, rv)
}

fn evaluate_rollout(gs: &mut GameState, max_steps: usize, rng: &mut FastRng) -> [f32; MAX_PLAYERS] {
    let mut steps = 0;
    while !gs.is_game_over && steps < max_steps {
        let act = heuristic_agent_action(gs, rng);
        if step(gs, act).is_err() {
            break;
        }
        steps += 1;
    }
    let mut vals = [0.0f32; MAX_PLAYERS];
    if let Some(w) = gs.winner {
        vals[w as usize] = 1.0;
    } else {
        // Heuristic evaluation if rollout truncated before game end
        let n = gs.num_players as usize;
        let mut scores = [0.0f32; MAX_PLAYERS];
        let mut sum = 0.0f32;
        for p in 0..n {
            let mut s = 1.0
                + gs.count_sites_ruled(p as PlayerId) as f32 * 1.5
                + gs.count_relics_and_banners(p as PlayerId) as f32 * 2.0
                + gs.players[p].favor as f32 * 0.2
                + gs.players[p].secrets_faceup as f32 * 0.4;
            if gs.oathkeeper_holder == Some(p as PlayerId) {
                s += 5.0;
            }
            scores[p] = s;
            sum += s;
        }
        if sum > 0.0 {
            for p in 0..n {
                vals[p] = scores[p] / sum;
            }
        }
    }
    vals
}

#[cfg(test)]
mod tests {
    use super::*;
    use oath_core::{create_initial_state, GameConfig};

    #[test]
    fn test_ismcts_search_returns_legal_action() {
        let cfg = GameConfig::default();
        let gs = create_initial_state(&cfg, None);
        let mcfg = MctsConfig {
            num_determinizations: 4,
            sims_per_det: 32,
            c_puct: 1.4,
            max_rollout_steps: 100,
            seed: 42,
        };
        let res = search_ismcts(&gs, 0, &mcfg, None);
        let mask = legal_mask(&gs);
        assert_eq!(mask[res.best_action as usize], 1);
        let sum_p: f32 = res.policy.iter().sum();
        assert!((sum_p - 1.0).abs() < 1e-4);
    }
}

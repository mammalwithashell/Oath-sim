#!/usr/bin/env python3
"""Vectorized RecurrentPPO (LSTM) trainer with:
1. Fast Native-Rust Behavioral Cloning (BC) warm-start from Role-Aware Bots
2. Proper per-player terminal credit assignment in multi-agent self-play
3. Sequence-chunked Truncated BPTT for LSTM memory
4. Curriculum (Random -> Role-Aware Bots -> Self-Play) + Unlimited Long Chronicles
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import oath_rs
from rl.model import OathLSTMNet


@torch.no_grad()
def evaluate_vs(
    model: OathLSTMNet,
    device: torch.device,
    opponent: str = "random",
    num_games: int = 20,
    seed: int = 9000,
    rl_seat: int = 1,
) -> float:
    """Evaluate trained OathLSTMNet as Exile seat `rl_seat` vs 3 Random or Role-Aware Bot seats."""
    model.eval()
    wins = 0
    for g in range(num_games):
        env = oath_rs.OathEnv(
            num_players=4,
            seed=seed + g * 31,
            first_game=False,
            oath_goal=g % 4,
            chronicle_enabled=False,
        )
        lstm_state = None
        step_i = 0
        while not env.is_game_over() and step_i < 2500:
            ap = env.acting_player()
            if ap == rl_seat:
                obs, cids, mask, _ = env.observe(ap)
                act_t, _, _, _, _, lstm_state = model.act(
                    torch.from_numpy(obs).unsqueeze(0).to(device),
                    torch.from_numpy(cids).unsqueeze(0).to(device),
                    torch.from_numpy(mask.astype(np.float32)).unsqueeze(0).to(device),
                    lstm_state,
                )
                act = int(act_t.item())
            elif opponent == "random":
                act = int(env.random_action(seed + g * 10000 + step_i))
            else:
                act = int(env.heuristic_action(seed + g * 10000 + step_i))
            env.step(act)
            step_i += 1
        if env.winner() == rl_seat:
            wins += 1
    model.train()
    return wins / max(num_games, 1) * 100.0


def run_bc_warmstart(
    model: OathLSTMNet,
    device: torch.device,
    num_samples: int,
    epochs: int,
    lr: float,
    seed: int,
) -> None:
    """Fast Behavioral Cloning warm-start from native-Rust Role-Aware Bots."""
    t0 = time.perf_counter()
    obs_np, cids_np, mask_np, act_np = oath_rs.collect_bot_dataset(
        num_samples=num_samples, num_players=4, seed=seed, chronicle_enabled=True
    )
    t_collect = time.perf_counter() - t0
    print(f"[BC Warm-Start] Collected {num_samples:,} bot transitions in {t_collect:.2f}s")

    t_obs = torch.from_numpy(obs_np).to(device)
    t_cids = torch.from_numpy(cids_np).to(device)
    t_mask = torch.from_numpy(mask_np.astype(np.float32)).to(device)
    t_act = torch.from_numpy(act_np.astype(np.int64)).to(device)

    opt = torch.optim.Adam(model.parameters(), lr=lr)
    bsz = 512
    for ep in range(1, epochs + 1):
        perm = torch.randperm(num_samples, device=device)
        total_loss = 0.0
        correct = 0
        batches = 0
        for s in range(0, num_samples, bsz):
            idx = perm[s : s + bsz]
            logits, _, _, _ = model(t_obs[idx], t_cids[idx], t_mask[idx])
            loss = F.cross_entropy(logits, t_act[idx])
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total_loss += float(loss.item())
            correct += int((logits.argmax(dim=-1) == t_act[idx]).sum().item())
            batches += 1
        acc = correct / num_samples * 100.0
        print(f"  BC Epoch {ep}/{epochs} | loss={total_loss/batches:.4f} | top1_acc={acc:.1f}%", flush=True)


@torch.no_grad()
def run_chronicle_saga(
    model: OathLSTMNet,
    device: torch.device,
    num_chronicles: int = 10,
    seed: int = 2026,
    out_path: str | None = "logs/chronicle_saga.jsonl",
) -> list[dict]:
    """Play a continuous multi-chronicle saga with 4 LSTM seats and log the emergent history."""
    model.eval()
    env = oath_rs.OathEnv(
        num_players=4,
        seed=seed,
        first_game=True,
        oath_goal=0,
        chronicle_enabled=True,
    )
    records = []
    for c_idx in range(1, num_chronicles + 1):
        if c_idx > 1:
            env.reset()
        init_st = json.loads(env.state_json())
        lstm_states = [None] * 4
        steps = 0
        while not env.is_game_over() and steps < 4000:
            ap = env.acting_player()
            obs, cids, mask, _ = env.observe(ap)
            act_t, _, _, _, _, next_st = model.act(
                torch.from_numpy(obs).unsqueeze(0).to(device),
                torch.from_numpy(cids).unsqueeze(0).to(device),
                torch.from_numpy(mask.astype(np.float32)).unsqueeze(0).to(device),
                lstm_states[ap],
            )
            lstm_states[ap] = next_st
            env.step(int(act_t.item()))
            steps += 1
        end_st = json.loads(env.state_json())
        winner = end_st["winner"]
        rec = {
            "chronicle": c_idx,
            "oath_goal": init_st["oath_goal"],
            "rounds": end_st["round_number"],
            "steps": steps,
            "start_roles": [p["role"] for p in init_st["players"][:4]],
            "end_roles": [p["role"] for p in end_st["players"][:4]],
            "winner": winner,
            "winner_role": end_st["players"][winner]["role"] if winner is not None else None,
            "win_type": end_st["win_type"],
            "vowed_oath": end_st["vowed_oath"],
            "dispossessed": len(init_st["dispossessed"]),
            "talk_events": len(end_st["talk_log"]),
            "sites": [oath_rs.card_info(s["site_id"])[1] for s in init_st["sites"] if s["is_faceup"]],
        }
        records.append(rec)

    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    model.train()
    return records


def make_vec_env(args: argparse.Namespace, stage: str, seed: int) -> oath_rs.VecOathEnv:
    if stage == "random":
        return oath_rs.VecOathEnv(
            num_envs=args.num_envs,
            num_players=args.num_players,
            base_seed=seed,
            single_agent_player=1,
            first_game=False,
            chronicle_enabled=args.chronicle,
            chronicle_max_length=args.chronicle_max_length,
            opponent_mode="random",
        )
    if stage == "bot":
        return oath_rs.VecOathEnv(
            num_envs=args.num_envs,
            num_players=args.num_players,
            base_seed=seed,
            single_agent_player=1,
            first_game=False,
            chronicle_enabled=args.chronicle,
            chronicle_max_length=args.chronicle_max_length,
            opponent_mode="bot",
        )
    return oath_rs.VecOathEnv(
        num_envs=args.num_envs,
        num_players=args.num_players,
        base_seed=seed,
        single_agent_player=None,
        first_game=False,
        chronicle_enabled=args.chronicle,
        chronicle_max_length=args.chronicle_max_length,
        opponent_mode="bot",
    )


def train(args: argparse.Namespace) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    steps_per_update = args.num_envs * args.rollout_steps
    total_updates = max(1, args.total_steps // steps_per_update)

    print(
        f"Training OathLSTMNet on {device} | hidden={args.hidden_size} | envs={args.num_envs} | "
        f"rollout={args.rollout_steps} | total_steps={total_updates * steps_per_update:,} ({total_updates} updates) | "
        f"chronicle={args.chronicle} (max_len={'unlimited' if args.chronicle_max_length == 0 else args.chronicle_max_length})"
    )

    model = OathLSTMNet(
        obs_flat_size=oath_rs.OBS_FLAT_SIZE,
        num_card_slots=oath_rs.OBS_CARD_IDS_SIZE,
        num_actions=oath_rs.NUM_ACTIONS,
        hidden_size=args.hidden_size,
    ).to(device)
    if args.resume and Path(args.resume).exists():
        ckpt = torch.load(args.resume, map_location=device, weights_only=True)
        model.load_state_dict(ckpt["model_state_dict"])
        print(f"Resumed weights from {args.resume}")
    elif args.bc_steps > 0:
        run_bc_warmstart(model, device, args.bc_steps, args.bc_epochs, args.bc_lr, args.seed)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # Curriculum: 20% Random -> 45% Role-Aware Bots -> 35% Multi-Agent Self-Play
    def stage_for_update(u: int) -> str:
        if not args.curriculum:
            return args.mode
        frac = (u - 1) / max(total_updates, 1)
        if frac < 0.20:
            return "random"
        if frac < 0.65:
            return "bot"
        return "self-play"

    current_stage = stage_for_update(1)
    env = make_vec_env(args, current_stage, args.seed)
    bot_anchor_env: oath_rs.VecOathEnv | None = None
    bot_anchor_obs = None
    bot_anchor_h = None
    bot_anchor_c = None

    obs_flat, card_ids, action_mask, acting_p = env.observe_all()
    lstm_h, lstm_c = model.init_hidden(args.num_envs, device)

    wr_rand0 = evaluate_vs(model, device, "random", num_games=20, seed=9000)
    wr_bot0 = evaluate_vs(model, device, "bot", num_games=20, seed=9500)
    best_eval_score = 0.3 * wr_rand0 + 0.7 * wr_bot0
    best_path = Path(args.save).with_name(Path(args.save).stem + "_best.pt") if args.save else None
    print(f"[Post-BC Init Eval] vs Random: {wr_rand0:5.1f}% | vs Role-Aware Bots: {wr_bot0:5.1f}% (4p uniform=25.0%)", flush=True)

    total_steps = 0
    total_episodes = 0
    stage_episodes = 0
    stage_wins = 0
    t0 = time.perf_counter()

    for update in range(1, total_updates + 1):
        desired_stage = stage_for_update(update)
        if desired_stage != current_stage:
            if desired_stage == "self-play":
                # Keep the active bot_env as an anchor (1/3 updates) to prevent self-play forgetting
                bot_anchor_env = env
                bot_anchor_obs = (obs_flat, card_ids, action_mask, acting_p)
                bot_anchor_h, bot_anchor_c = lstm_h, lstm_c
            current_stage = desired_stage
            env = make_vec_env(args, current_stage, args.seed + update * 97)
            obs_flat, card_ids, action_mask, acting_p = env.observe_all()
            lstm_h, lstm_c = model.init_hidden(args.num_envs, device)
            stage_episodes = 0
            stage_wins = 0
            print(f"\n>>> Curriculum Stage Transition -> [{current_stage.upper()}] at step {total_steps:,}", flush=True)

        # During self-play, run every 3rd update on the bot anchor env to prevent forgetting
        use_anchor = current_stage == "self-play" and bot_anchor_env is not None and (update % 3 == 0)
        if use_anchor:
            active_env = bot_anchor_env
            active_stage = "bot-anc"
            cur_obs_flat, cur_cids, cur_mask, cur_ap = bot_anchor_obs
            cur_h, cur_c = bot_anchor_h, bot_anchor_c
        else:
            active_env = env
            active_stage = current_stage
            cur_obs_flat, cur_cids, cur_mask, cur_ap = obs_flat, card_ids, action_mask, acting_p
            cur_h, cur_c = lstm_h, lstm_c

        # Save initial hidden states for Truncated BPTT!
        init_h = cur_h.detach().clone()
        init_c = cur_c.detach().clone()

        buf_obs, buf_cids, buf_mask = [], [], []
        buf_act, buf_logp, buf_val, buf_rew, buf_done = [], [], [], [], []
        buf_actors = []

        for t in range(args.rollout_steps):
            t_obs = torch.from_numpy(cur_obs_flat).to(device)
            t_cids = torch.from_numpy(cur_cids).to(device)
            t_mask = torch.from_numpy(cur_mask.astype(np.float32)).to(device)
            cur_actors = cur_ap.copy()

            action, logp, val, _, _, (cur_h, cur_c) = model.act(
                t_obs, t_cids, t_mask, (cur_h, cur_c)
            )
            act_np = action.cpu().numpy().astype(np.uint16)
            next_obs, next_cids, next_mask, rewards, dones, next_ap, winners = active_env.step_all(act_np)

            rew_arr = rewards.copy()
            # In multi-agent self-play, assign terminal +1/-1 to EVERY player's last step in the rollout
            if active_stage == "self-play" and dones.any():
                for e_idx in np.where(dones)[0]:
                    w = int(winners[e_idx])
                    if w < 0:
                        continue
                    seen = set()
                    if cur_actors[e_idx] == w:
                        rew_arr[e_idx] = 1.0
                    else:
                        rew_arr[e_idx] = -1.0
                    seen.add(int(cur_actors[e_idx]))
                    for back_t in range(len(buf_actors) - 1, -1, -1):
                        if buf_done[back_t][e_idx].item() > 0.5:
                            break
                        p_back = int(buf_actors[back_t][e_idx])
                        if p_back not in seen:
                            buf_rew[back_t][e_idx] += 1.0 if p_back == w else -1.0
                            seen.add(p_back)
                            if len(seen) >= args.num_players:
                                break

            buf_obs.append(t_obs)
            buf_cids.append(t_cids)
            buf_mask.append(t_mask)
            buf_act.append(action)
            buf_logp.append(logp)
            buf_val.append(val)
            buf_rew.append(torch.from_numpy(rew_arr).to(device))
            buf_done.append(torch.from_numpy(dones.astype(np.float32)).to(device))
            buf_actors.append(cur_actors)

            if dones.any():
                done_idx = np.where(dones)[0]
                total_episodes += len(done_idx)
                stage_episodes += len(done_idx)
                if active_stage == "self-play":
                    stage_wins += int((winners[done_idx] > 0).sum())
                else:
                    stage_wins += int((winners[done_idx] == 1).sum())
                done_t = torch.from_numpy(done_idx).to(device)
                cur_h[:, done_t, :] = 0.0
                cur_c[:, done_t, :] = 0.0

            cur_obs_flat, cur_cids, cur_mask, cur_ap = next_obs, next_cids, next_mask, next_ap
            total_steps += args.num_envs

        if use_anchor:
            bot_anchor_obs = (cur_obs_flat, cur_cids, cur_mask, cur_ap)
            bot_anchor_h, bot_anchor_c = cur_h, cur_c
        else:
            obs_flat, card_ids, action_mask, acting_p = cur_obs_flat, cur_cids, cur_mask, cur_ap
            lstm_h, lstm_c = cur_h, cur_c

        with torch.no_grad():
            _, last_val, _, _ = model(
                torch.from_numpy(cur_obs_flat).to(device),
                torch.from_numpy(cur_cids).to(device),
                torch.from_numpy(cur_mask.astype(np.float32)).to(device),
                (cur_h, cur_c),
            )

        T = args.rollout_steps
        adv = torch.zeros(T, args.num_envs, device=device)
        gae = torch.zeros(args.num_envs, device=device)
        for t in reversed(range(T)):
            next_v = last_val if t == T - 1 else buf_val[t + 1]
            non_term = 1.0 - buf_done[t]
            delta = buf_rew[t] + args.gamma * next_v * non_term - buf_val[t]
            gae = delta + args.gamma * args.gae_lambda * non_term * gae
            adv[t] = gae

        # Shape as (N_envs, T, ...) for genuine Truncated BPTT!
        seq_obs = torch.stack(buf_obs, dim=1)     # (N, T, F)
        seq_cids = torch.stack(buf_cids, dim=1)   # (N, T, C)
        seq_mask = torch.stack(buf_mask, dim=1)   # (N, T, A)
        seq_act = torch.stack(buf_act, dim=1)     # (N, T)
        seq_logp = torch.stack(buf_logp, dim=1)   # (N, T)
        seq_done = torch.stack(buf_done, dim=1)   # (N, T)
        seq_adv = adv.transpose(0, 1)             # (N, T)
        seq_ret = (adv + torch.stack(buf_val)).transpose(0, 1)
        seq_adv = (seq_adv - seq_adv.mean()) / (seq_adv.std() + 1e-8)

        env_mb = max(1, args.num_envs // 4)
        last_loss = 0.0
        for _ in range(args.ppo_epochs):
            env_perm = torch.randperm(args.num_envs, device=device)
            for s in range(0, args.num_envs, env_mb):
                e_idx = env_perm[s : s + env_mb]
                logits, values = model.forward_sequence(
                    seq_obs[e_idx],
                    seq_cids[e_idx],
                    seq_mask[e_idx],
                    seq_done[e_idx],
                    (init_h[:, e_idx, :], init_c[:, e_idx, :]),
                )
                probs = F.softmax(logits, dim=-1)
                dist = torch.distributions.Categorical(probs=probs)
                new_logp = dist.log_prob(seq_act[e_idx])
                entropy = dist.entropy().mean()

                ratio = torch.exp(new_logp - seq_logp[e_idx])
                surr1 = ratio * seq_adv[e_idx]
                surr2 = torch.clamp(ratio, 1.0 - args.clip_eps, 1.0 + args.clip_eps) * seq_adv[e_idx]
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = F.mse_loss(values, seq_ret[e_idx])
                loss = policy_loss + 0.5 * value_loss - args.ent_coef * entropy

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                optimizer.step()
                last_loss = float(loss.item())

        elapsed = time.perf_counter() - t0
        sps = total_steps / max(elapsed, 1e-6)
        wr_stage = (stage_wins / stage_episodes * 100.0) if stage_episodes > 0 else 0.0
        wr_label = "exile_win%" if current_stage == "self-play" else "stage_win%"
        if update % args.log_every == 0 or update == total_updates:
            print(
                f"Upd {update:4d}/{total_updates} [{current_stage:9s}] | steps={total_steps:7,d} | "
                f"sps={sps:6.0f} | eps={total_episodes:5d} | {wr_label}={wr_stage:5.1f}% | loss={last_loss:.4f}",
                flush=True,
            )

        if args.eval_every > 0 and (update % args.eval_every == 0 or update == total_updates):
            wr_rand = evaluate_vs(model, device, "random", num_games=20, seed=9000 + update)
            wr_bot = evaluate_vs(model, device, "bot", num_games=20, seed=9500 + update)
            eval_score = 0.3 * wr_rand + 0.7 * wr_bot
            star = ""
            if best_path is not None and eval_score >= best_eval_score:
                best_eval_score = eval_score
                best_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "hidden_size": args.hidden_size,
                        "num_actions": oath_rs.NUM_ACTIONS,
                        "obs_flat_size": oath_rs.OBS_FLAT_SIZE,
                        "num_card_slots": oath_rs.OBS_CARD_IDS_SIZE,
                        "eval_vs_random": wr_rand,
                        "eval_vs_bot": wr_bot,
                    },
                    best_path,
                )
                star = f"  ★ NEW BEST ({best_path.name})"
            print(
                f"  >>> [Eval @ {total_steps:,} steps] vs Random: {wr_rand:5.1f}% | vs Role-Aware Bots: {wr_bot:5.1f}%{star}",
                flush=True,
            )

    if args.save:
        out_path = Path(args.save)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "hidden_size": args.hidden_size,
                "num_actions": oath_rs.NUM_ACTIONS,
                "obs_flat_size": oath_rs.OBS_FLAT_SIZE,
                "num_card_slots": oath_rs.OBS_CARD_IDS_SIZE,
            },
            out_path,
        )
        print(f"Saved latest checkpoint to {out_path}")

    if args.saga_games > 0:
        if best_path is not None and best_path.exists():
            ckpt = torch.load(best_path, map_location=device, weights_only=True)
            model.load_state_dict(ckpt["model_state_dict"])
            print(f"\n=== Emergent {args.saga_games}-Chronicle Self-Play Saga (using {best_path.name}) ===")
        else:
            print(f"\n=== Emergent {args.saga_games}-Chronicle Self-Play Saga ===")
        recs = run_chronicle_saga(model, device, num_chronicles=args.saga_games)
        for r in recs:
            print(
                f"  Year {r['chronicle']:2d} | Oath={r['oath_goal']:9s} | R={r['rounds']} | "
                f"Winner=P{r['winner']}({r['winner_role']:10s}) via {r['win_type']:17s} | "
                f"Vowed={str(r['vowed_oath']):9s} | Dispossessed={r['dispossessed']:3d}"
            )


def main() -> None:
    p = argparse.ArgumentParser(description="Train OathLSTMNet with Rust VecOathEnv")
    p.add_argument("--total-steps", type=int, default=250_000)
    p.add_argument("--num-envs", type=int, default=64)
    p.add_argument("--num-players", type=int, default=4)
    p.add_argument("--rollout-steps", type=int, default=64)
    p.add_argument("--ppo-epochs", type=int, default=2)
    p.add_argument("--hidden-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1.5e-4)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--clip-eps", type=float, default=0.2)
    p.add_argument("--ent-coef", type=float, default=0.02)
    p.add_argument("--bc-steps", type=int, default=40_000)
    p.add_argument("--bc-epochs", type=int, default=6)
    p.add_argument("--bc-lr", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--curriculum", action="store_true", help="Random -> Role-Aware Bots -> Self-Play")
    p.add_argument("--mode", choices=["random", "bot", "self-play"], default="bot")
    p.add_argument("--chronicle", action="store_true", help="Enable continuous multi-game Chronicles")
    p.add_argument("--chronicle-max-length", type=int, default=0, help="0 = unlimited continuous chronicle")
    p.add_argument("--resume", type=str, default=None)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--eval-every", type=int, default=20)
    p.add_argument("--saga-games", type=int, default=10)
    p.add_argument("--save", type=str, default="models/oath_lstm_latest.pt")
    train(p.parse_args())


if __name__ == "__main__":
    main()

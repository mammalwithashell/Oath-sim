#!/usr/bin/env python3
"""Profile Rust VecOathEnv vs PyTorch OathLSTMNet rollout & PPO update bottlenecks."""
from __future__ import annotations

import os
import time
import numpy as np
import torch
import torch.nn.functional as F

import oath_rs
from rl.model import OathLSTMNet


def main() -> None:
    print(f"CPU cores: {os.cpu_count()} | PyTorch threads: {torch.get_num_threads()} | CUDA: {torch.cuda.is_available()}")

    # 1. Pure Rust VecOathEnv scaling
    print("\n=== 1. Pure Rust VecOathEnv Throughput (self-play, no NN) ===")
    for n_envs in [16, 32, 64, 128]:
        vec = oath_rs.VecOathEnv(num_envs=n_envs, num_players=4, base_seed=42, single_agent_player=None)
        obs, cids, mask, _ = vec.observe_all()
        n_steps = 200
        t0 = time.perf_counter()
        for _ in range(n_steps):
            acts = np.argmax(mask, axis=1).astype(np.uint16)
            obs, cids, mask, _, _, _ = vec.step_all(acts)
        dt = time.perf_counter() - t0
        print(f"  num_envs={n_envs:3d}: {n_envs * n_steps / dt:10,.0f} env-steps/sec ({dt*1000/n_steps:.2f} ms/batch)")

    # 2. Breakdown of a full RecurrentPPO iteration (num_envs=64, rollout=64 -> 4096 steps/update)
    print("\n=== 2. RecurrentPPO Step Breakdown (num_envs=64, rollout=64, 4096 steps) ===")
    n_envs, rollout = 64, 64
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vec = oath_rs.VecOathEnv(num_envs=n_envs, num_players=4, base_seed=99, single_agent_player=None)
    model = OathLSTMNet(hidden_size=256).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=3e-4)

    obs, cids, mask, _ = vec.observe_all()
    h, c = model.init_hidden(n_envs, device)

    t_env = 0.0
    t_infer = 0.0
    t_copy = 0.0
    buf_obs, buf_cids, buf_mask, buf_act = [], [], [], []

    for _ in range(rollout):
        tc0 = time.perf_counter()
        to = torch.from_numpy(obs).to(device)
        tc = torch.from_numpy(cids).to(device)
        tm = torch.from_numpy(mask.astype(np.float32)).to(device)
        t_copy += time.perf_counter() - tc0

        ti0 = time.perf_counter()
        act, _, _, _, _, (h, c) = model.act(to, tc, tm, (h, c))
        act_np = act.cpu().numpy().astype(np.uint16)
        t_infer += time.perf_counter() - ti0

        te0 = time.perf_counter()
        obs, cids, mask, _, dones, _ = vec.step_all(act_np)
        t_env += time.perf_counter() - te0

        buf_obs.append(to)
        buf_cids.append(tc)
        buf_mask.append(tm)
        buf_act.append(act)
        if dones.any():
            didx = torch.from_numpy(np.where(dones)[0]).to(device)
            h[:, didx, :] = 0.0
            c[:, didx, :] = 0.0

    # Measure 1 PPO epoch (4 minibatches of 1024)
    b_obs = torch.stack(buf_obs).reshape(-1, oath_rs.OBS_FLAT_SIZE)
    b_cids = torch.stack(buf_cids).reshape(-1, oath_rs.OBS_CARD_IDS_SIZE)
    b_mask = torch.stack(buf_mask).reshape(-1, oath_rs.NUM_ACTIONS)
    b_act = torch.stack(buf_act).reshape(-1)

    t_ppo0 = time.perf_counter()
    for mb in range(0, len(b_obs), 1024):
        logits, vals, _, _ = model(b_obs[mb:mb+1024], b_cids[mb:mb+1024], b_mask[mb:mb+1024])
        loss = F.cross_entropy(logits, b_act[mb:mb+1024]) + 0.5 * (vals ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    t_ppo = time.perf_counter() - t_ppo0

    total = t_env + t_infer + t_copy + t_ppo
    steps = n_envs * rollout
    print(f"  Rust env.step_all : {t_env*1000:7.1f} ms ({t_env/total*100:5.1f}%)")
    print(f"  NumPy->Torch copy : {t_copy*1000:7.1f} ms ({t_copy/total*100:5.1f}%)")
    print(f"  PyTorch inference : {t_infer*1000:7.1f} ms ({t_infer/total*100:5.1f}%)")
    print(f"  PyTorch PPO epoch : {t_ppo*1000:7.1f} ms ({t_ppo/total*100:5.1f}%)")
    print(f"  TOTAL (4096 steps): {total*1000:7.1f} ms -> {steps/total:,.0f} steps/sec on {device}")
    print(f"  (With a desktop GPU doing inference+PPO in ~15ms, Rust env alone supports ~{steps/t_env:,.0f} steps/sec!)")


if __name__ == "__main__":
    main()

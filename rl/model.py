"""OathLSTMNet: Shared Card-Embedding + LSTM Actor-Critic / AlphaZero Network."""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class OathLSTMNet(nn.Module):
    """Recurrent neural network for imperfect-information Oath RL & AlphaZero search.

    Inputs:
        obs_flat: (B, 1024) float32 player-relative state tensor
        card_ids: (B, 64)   int64 card IDs (0=empty, 1..259=cards, 260=unknown facedown)
        action_mask: (B, 216) float32/bool binary legal action mask
        lstm_state: optional tuple (h, c) each of shape (1, B, hidden_size)

    Outputs:
        logits: (B, 216) masked action logits
        value:  (B,)     scalar value estimate for acting player
        mp_values: (B, 6) multi-player win-probability logits (for AlphaZero IS-MCTS)
        next_lstm_state: (h, c)
    """

    def __init__(
        self,
        obs_flat_size: int = 1024,
        num_card_slots: int = 64,
        num_card_vocab: int = 261,
        card_embed_dim: int = 24,
        num_actions: int = 216,
        hidden_size: int = 256,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_actions = num_actions

        self.card_embed = nn.Embedding(num_card_vocab, card_embed_dim, padding_idx=0)
        self.card_proj = nn.Sequential(
            nn.Linear(num_card_slots * card_embed_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
        )
        self.flat_proj = nn.Sequential(
            nn.Linear(obs_flat_size, 384),
            nn.LayerNorm(384),
            nn.GELU(),
        )
        self.fuse = nn.Sequential(
            nn.Linear(384 + 256, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
        )
        self.lstm = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.policy_head = nn.Linear(hidden_size, num_actions)
        self.value_head = nn.Linear(hidden_size, 1)
        self.mp_value_head = nn.Linear(hidden_size, 6)

    def init_hidden(self, batch_size: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        h = torch.zeros(1, batch_size, self.hidden_size, device=device)
        c = torch.zeros(1, batch_size, self.hidden_size, device=device)
        return h, c

    def forward(
        self,
        obs_flat: torch.Tensor,
        card_ids: torch.Tensor,
        action_mask: torch.Tensor,
        lstm_state: tuple[torch.Tensor, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        bsz = obs_flat.shape[0]
        if lstm_state is None:
            lstm_state = self.init_hidden(bsz, obs_flat.device)

        c_emb = self.card_embed(card_ids.long()).reshape(bsz, -1)
        c_feat = self.card_proj(c_emb)
        f_feat = self.flat_proj(obs_flat)
        fused = self.fuse(torch.cat([f_feat, c_feat], dim=-1)).unsqueeze(1)

        out, next_state = self.lstm(fused, lstm_state)
        h = out.squeeze(1)

        raw_logits = self.policy_head(h)
        mask_bool = action_mask > 0.5
        logits = raw_logits.masked_fill(~mask_bool, -1e9)
        value = self.value_head(h).squeeze(-1)
        mp_values = F.softmax(self.mp_value_head(h), dim=-1)
        return logits, value, mp_values, next_state

    def forward_sequence(
        self,
        obs_flat: torch.Tensor,      # (B, T, obs_flat_size)
        card_ids: torch.Tensor,      # (B, T, num_card_slots)
        action_mask: torch.Tensor,   # (B, T, num_actions)
        dones: torch.Tensor,         # (B, T) float32 (1.0 after terminal step)
        init_state: tuple[torch.Tensor, torch.Tensor],  # (1, B, H)
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Truncated BPTT over (B, T) sequences, resetting LSTM state on episode boundaries."""
        bsz, seq_len, _ = obs_flat.shape
        c_emb = self.card_embed(card_ids.long()).reshape(bsz * seq_len, -1)
        c_feat = self.card_proj(c_emb)
        f_feat = self.flat_proj(obs_flat.reshape(bsz * seq_len, -1))
        fused = self.fuse(torch.cat([f_feat, c_feat], dim=-1)).reshape(bsz, seq_len, -1)

        h, c = init_state
        outs = []
        for t in range(seq_len):
            out_t, (h, c) = self.lstm(fused[:, t : t + 1, :], (h, c))
            outs.append(out_t.squeeze(1))
            # Reset hidden state for environments that terminated on step t
            keep = (1.0 - dones[:, t]).view(1, bsz, 1)
            h = h * keep
            c = c * keep

        h_seq = torch.stack(outs, dim=1)  # (B, T, H)
        raw_logits = self.policy_head(h_seq)
        logits = raw_logits.masked_fill(~(action_mask > 0.5), -1e9)
        values = self.value_head(h_seq).squeeze(-1)
        return logits, values

    @torch.no_grad()
    def act(
        self,
        obs_flat: torch.Tensor,
        card_ids: torch.Tensor,
        action_mask: torch.Tensor,
        lstm_state: tuple[torch.Tensor, torch.Tensor] | None = None,
        deterministic: bool = False,
    ):
        logits, value, mp_values, next_state = self.forward(
            obs_flat, card_ids, action_mask, lstm_state
        )
        probs = F.softmax(logits, dim=-1)
        if deterministic:
            action = probs.argmax(dim=-1)
        else:
            dist = torch.distributions.Categorical(probs=probs)
            action = dist.sample()
        log_prob = torch.log(probs.gather(-1, action.unsqueeze(-1)).squeeze(-1) + 1e-10)
        return action, log_prob, value, probs, mp_values, next_state

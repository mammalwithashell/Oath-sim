"""Uniform random legal action agent."""

from __future__ import annotations

from typing import Optional

import numpy as np


class RandomAgent:
    """Agent that selects uniformly at random from legal actions."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def act(self, observation: dict) -> int:
        """Select a random legal action."""
        mask = observation["action_mask"]
        legal_actions = np.where(mask > 0.5)[0]
        if len(legal_actions) == 0:
            return 43  # END_ACT_PHASE as fallback
        return int(self.rng.choice(legal_actions))

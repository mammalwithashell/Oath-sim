"""Rule-based heuristic agent for Oath simulator."""

from __future__ import annotations

from typing import Optional

import numpy as np


class HeuristicAgent:
    """Agent with simple heuristic priorities.

    Priority order:
    1. Search if supply allows
    2. Muster if at a site with cards
    3. Trade for favor/secrets
    4. Travel to a new site
    5. End act phase
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def act(self, observation: dict) -> int:
        """Select action based on heuristic priorities."""
        mask = observation["action_mask"]
        legal = np.where(mask > 0.5)[0]

        if len(legal) == 0:
            return 43  # END_ACT_PHASE fallback

        # Compound action states — pick first legal
        compound_ranges = [(56, 101), (49, 55), (60, 85)]
        for lo, hi in compound_ranges:
            in_range = [a for a in legal if lo <= a <= hi]
            if in_range:
                return int(self.rng.choice(in_range))

        # Search (prefer deck)
        if 8 in legal:
            return 8
        if 9 in legal:
            return 9

        # Muster
        muster = [a for a in legal if 10 <= a <= 12]
        if muster:
            return int(self.rng.choice(muster))

        # Trade
        trade = [a for a in legal if 13 <= a <= 18]
        if trade:
            return int(self.rng.choice(trade))

        # Recover
        recover = [a for a in legal if 19 <= a <= 23]
        if recover:
            return int(self.rng.choice(recover))

        # Travel
        travel = [a for a in legal if 0 <= a <= 7]
        if travel:
            return int(self.rng.choice(travel))

        # Campaign
        campaign = [a for a in legal if 24 <= a <= 28]
        if campaign and self.rng.random() < 0.3:
            return int(self.rng.choice(campaign))

        # End act phase
        if 43 in legal:
            return 43

        return int(self.rng.choice(legal))

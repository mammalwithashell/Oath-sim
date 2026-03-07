"""Player state dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from oath.enums import Role


@dataclass
class PlayerState:
    """Mutable state for a single player."""
    role: Role
    pawn_site: int = 0  # Site index (0–7)
    supply: int = 7
    warbands_board: int = 0  # Deployed on sites
    warbands_bank: int = 0  # Available in personal bank
    favor: int = 0
    secrets: int = 0
    advisers: list[Optional[int]] = field(default_factory=lambda: [None, None, None])
    adviser_faceup: list[bool] = field(default_factory=lambda: [False, False, False])
    relics: list[int] = field(default_factory=list)
    revealed_vision: Optional[int] = None
    color: int = 0

    @property
    def num_advisers(self) -> int:
        return sum(1 for a in self.advisers if a is not None)

    def first_empty_adviser_slot(self) -> Optional[int]:
        for i, a in enumerate(self.advisers):
            if a is None:
                return i
        return None

    def total_warbands(self) -> int:
        return self.warbands_board + self.warbands_bank

"""Banner state for People's Favor and Darkest Secret."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BannerState:
    """State of the People's Favor and Darkest Secret banners."""
    peoples_favor_holder: Optional[int] = None
    peoples_favor_tokens: int = 0
    peoples_favor_is_mob: bool = False

    darkest_secret_holder: Optional[int] = None
    darkest_secret_tokens: int = 0

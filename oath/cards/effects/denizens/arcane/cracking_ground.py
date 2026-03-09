"""Cracking Ground (OATH-071) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 72: Cracking Ground ───────────────────────────────────────
# Battle Plan: +/- defense dice per site targeted.
def _cracking_ground_execute(gs: 'GameState', player_index: int) -> 'GameState':
    cs = gs.compound_state
    if cs is None:
        return gs
    # Count number of targeted sites
    site_targets = sum(1 for t in cs.campaign_targets if t.startswith("site:"))
    if cs.campaign_attacker == player_index:
        cs.campaign_attack_dice += site_targets
    elif cs.campaign_defender == player_index:
        cs.campaign_defense_dice = max(0, cs.campaign_defense_dice - site_targets)
    return gs

register_effect(72, CardEffect(
    trigger=EffectTrigger.BATTLE_PLAN,
    condition=always_true,
    execute=_cracking_ground_execute,
    description="Battle Plan: +/- defense dice per site targeted",
))

"""Blood Pact (OATH-062) — Denizen (Arcane)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import gain_secrets, has_warbands_on_board

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 63: Blood Pact ────────────────────────────────────────────
# Action: Sacrifice 2 warbands on board, gain 1 secret.
def _blood_pact_execute(gs: 'GameState', player_index: int) -> 'GameState':
    player = gs.players[player_index]
    player.warbands_board -= 2
    return gain_secrets(gs, player_index, 1)

register_effect(63, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=has_warbands_on_board(2),
    execute=_blood_pact_execute,
    description="Action: Sacrifice 2 warbands, gain 1 secret",
))

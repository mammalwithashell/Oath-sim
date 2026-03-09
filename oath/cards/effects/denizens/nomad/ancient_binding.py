"""Ancient Binding (OATH-023) — Denizen (Nomad)."""
from __future__ import annotations
from typing import TYPE_CHECKING

from oath.cards.effects._base import register_effect, CardEffect
from oath.enums import EffectTrigger
from oath.cards.effects._helpers import always_true

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── ID 31: Ancient Binding ───────────────────────────────────────
# ACTION: Each player burns all secrets except last.
def _ancient_binding_execute(gs: 'GameState', player_index: int) -> 'GameState':
    for i in range(len(gs.players)):
        player = gs.players[i]
        if player.secrets > 1:
            excess = player.secrets - 1
            player.secrets = 1
            gs.shared_secrets += excess
    return gs

register_effect(31, CardEffect(
    trigger=EffectTrigger.ACTION,
    condition=always_true,
    execute=_ancient_binding_execute,
    description="Action: Each player burns all secrets except last",
))

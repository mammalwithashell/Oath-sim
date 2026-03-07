"""Reusable effect building blocks for Oath card effects."""

from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

from oath.enums import Suit, Role, MAX_ADVISERS, MAX_SITES

if TYPE_CHECKING:
    from oath.state.game_state import GameState


# ── Resource Helpers ──────────────────────────────────────────────

def gain_favor(gs: 'GameState', player_index: int, amount: int,
               suit: Optional[Suit] = None) -> 'GameState':
    """Player gains favor. If suit specified, take from that bank."""
    if suit is not None:
        bank_idx = int(suit)
        taken = min(amount, gs.favor_banks[bank_idx])
        gs.favor_banks[bank_idx] -= taken
        gs.players[player_index].favor += taken
    else:
        gs.players[player_index].favor += amount
    return gs


def gain_favor_from_banks(gs: 'GameState', player_index: int,
                          amount: int) -> 'GameState':
    """Player gains favor from any available banks (takes from largest first)."""
    remaining = amount
    while remaining > 0:
        best_bank = max(range(len(gs.favor_banks)), key=lambda i: gs.favor_banks[i])
        if gs.favor_banks[best_bank] <= 0:
            break
        taken = min(remaining, gs.favor_banks[best_bank])
        gs.favor_banks[best_bank] -= taken
        gs.players[player_index].favor += taken
        remaining -= taken
    return gs


def gain_secrets(gs: 'GameState', player_index: int, amount: int) -> 'GameState':
    """Player gains secrets from the shared pool."""
    taken = min(amount, gs.shared_secrets)
    gs.shared_secrets -= taken
    gs.players[player_index].secrets += taken
    return gs


def spend_favor(gs: 'GameState', player_index: int, amount: int) -> 'GameState':
    """Player spends favor (just reduces their count)."""
    gs.players[player_index].favor -= amount
    return gs


def spend_secrets(gs: 'GameState', player_index: int, amount: int) -> 'GameState':
    """Player spends secrets (just reduces their count)."""
    gs.players[player_index].secrets -= amount
    return gs


def burn_favor(gs: 'GameState', player_index: int, amount: int,
               suit: Optional[Suit] = None) -> 'GameState':
    """Player returns favor to a bank."""
    actual = min(amount, gs.players[player_index].favor)
    gs.players[player_index].favor -= actual
    if suit is not None:
        gs.favor_banks[int(suit)] += actual
    return gs


def burn_secrets(gs: 'GameState', player_index: int, amount: int) -> 'GameState':
    """Player returns secrets to the shared pool."""
    actual = min(amount, gs.players[player_index].secrets)
    gs.players[player_index].secrets -= actual
    gs.shared_secrets += actual
    return gs


# ── Warband Helpers ───────────────────────────────────────────────

def gain_warbands(gs: 'GameState', player_index: int, count: int) -> 'GameState':
    """Player gains warbands from their bank to their board (not placed at site)."""
    player = gs.players[player_index]
    actual = min(count, player.warbands_bank)
    player.warbands_bank -= actual
    player.warbands_board += actual
    return gs


def place_warbands_at_site(gs: 'GameState', player_index: int,
                           site_index: int, count: int) -> 'GameState':
    """Place warbands from player's bank onto a site."""
    player = gs.players[player_index]
    actual = min(count, player.warbands_bank)
    player.warbands_bank -= actual
    player.warbands_board += actual
    gs.sites[site_index].warbands += actual
    return gs


def kill_warbands(gs: 'GameState', target_player: int,
                  site_index: int, count: int) -> 'GameState':
    """Kill warbands belonging to target at a site."""
    player = gs.players[target_player]
    site = gs.sites[site_index]
    actual = min(count, site.warbands, player.warbands_board)
    site.warbands -= actual
    player.warbands_board -= actual
    return gs


# ── Supply Helpers ────────────────────────────────────────────────

def gain_supply(gs: 'GameState', player_index: int, amount: int) -> 'GameState':
    """Player gains supply."""
    gs.players[player_index].supply += amount
    return gs


# ── Condition Builders ────────────────────────────────────────────

def always_true(gs: 'GameState', player_index: int) -> bool:
    """Condition that always returns True."""
    return True


def has_rule(gs: 'GameState', player_index: int) -> bool:
    """Check if player rules any site."""
    return any(s.ruling_player == player_index for s in gs.sites)


def is_role(role: Role) -> Callable[['GameState', int], bool]:
    """Return a condition that checks if player has a specific role."""
    def _check(gs: 'GameState', player_index: int) -> bool:
        return gs.players[player_index].role == role
    return _check


def has_min_favor(amount: int) -> Callable[['GameState', int], bool]:
    """Return a condition that checks if player has minimum favor."""
    def _check(gs: 'GameState', player_index: int) -> bool:
        return gs.players[player_index].favor >= amount
    return _check


def has_min_secrets(amount: int) -> Callable[['GameState', int], bool]:
    """Return a condition that checks if player has minimum secrets."""
    def _check(gs: 'GameState', player_index: int) -> bool:
        return gs.players[player_index].secrets >= amount
    return _check


def player_rules_site(gs: 'GameState', player_index: int,
                      site_index: int) -> bool:
    """Check if player rules a specific site."""
    return gs.sites[site_index].ruling_player == player_index


def count_ruled_sites(gs: 'GameState', player_index: int) -> int:
    """Count how many sites a player rules."""
    return sum(1 for s in gs.sites if s.ruling_player == player_index and s.is_faceup)

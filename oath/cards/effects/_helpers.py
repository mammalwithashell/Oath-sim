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
    site = gs.sites[site_index]
    site.warbands += actual
    if actual > 0:
        site.warband_color = 0 if gs.is_imperial(player_index) else player_index
    return gs


def kill_warbands(gs: 'GameState', target_player: int,
                  site_index: int, count: int) -> 'GameState':
    """Kill warbands belonging to target at a site."""
    player = gs.players[target_player]
    site = gs.sites[site_index]
    actual = min(count, site.warbands, player.warbands_board)
    site.warbands -= actual
    player.warbands_board -= actual
    if site.warbands <= 0:
        site.warbands = 0
        site.ruling_player = None
        site.warband_color = None
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
    return gs.count_sites_ruled(player_index) > 0


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
    """Check if player rules a specific site (Imperial sharing aware)."""
    site = gs.sites[site_index]
    if site.ruling_player == player_index:
        return True
    # Imperial sharing: Chancellor and Citizens share rule over Imperial sites
    if (gs.is_imperial(player_index)
            and site.ruling_player is not None
            and gs.is_imperial(site.ruling_player)
            and site.warband_color == 0
            and site.warbands > 0):
        return True
    return False


def count_ruled_sites(gs: 'GameState', player_index: int) -> int:
    """Count how many sites a player rules."""
    return gs.count_sites_ruled(player_index)


def has_darkest_secret(gs: 'GameState', player_index: int) -> bool:
    """Check if player holds the Darkest Secret."""
    return gs.darkest_secret_holder == player_index


def has_warbands_on_board(min_count: int):
    """Return a condition checking player has at least min_count warbands on board."""
    def _check(gs: 'GameState', player_index: int) -> bool:
        return gs.players[player_index].warbands_board >= min_count
    return _check


def has_secrets_and_player_at_site(gs: 'GameState', player_index: int) -> bool:
    """Check if player has secrets and another player is at the same site."""
    player = gs.players[player_index]
    if player.secrets < 1:
        return False
    for i, p in enumerate(gs.players):
        if i != player_index and p.pawn_site == player.pawn_site:
            return True
    return False

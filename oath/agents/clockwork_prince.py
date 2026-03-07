"""Clockwork Prince automated Chancellor opponent for Oath simulator.

Implements the official Oath solo-play automa from the Clockwork Prince
Print-and-Play rules. The Prince replaces the Chancellor (player 0) and
follows a deterministic flowchart to select actions based on threat assessment.

This agent uses Limited Powers mode: it benefits from free card powers
(battle plans, modifiers) but won't spend favor, secrets, or discard cards
to use powers.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import numpy as np

from oath.enums import (
    Suit, Role, Phase, Region, CompoundStateType,
    SuccessorGoal, TitleSide, CardRestriction,
    MAX_SITES, MAX_ADVISERS, NUM_ACTIONS,
)
from oath.cards.database import get_card

if TYPE_CHECKING:
    from oath.state.game_state import GameState

# ── Mind quadrants ────────────────────────────────────────────────
# Each quadrant corresponds to a threat type and determines:
#   - Which suit of card to play (Friend or Conspirator)
#   - Which actions to take from the flowchart
QUADRANT_SUCCESSOR = "successor"   # Top-Left: Play highest Friend
QUADRANT_OATHKEEPER = "oathkeeper" # Top-Right: Play highest Conspirator
QUADRANT_DS = "darkest_secret"     # Bottom-Left: Play highest Conspirator
QUADRANT_PF = "peoples_favor"      # Bottom-Right: Play highest Friend

# Tactics thresholds where caution decreases
_TACTICS_CAUTION_THRESHOLDS = {3, 5, 6}


class ClockworkPrinceAgent:
    """Automated Chancellor opponent based on the Clockwork Prince rules.

    The Prince maintains internal state (tactics, caution, relationships)
    and follows the Mind flowchart to select actions each turn.

    Usage:
        prince = ClockworkPrinceAgent()
        prince.set_game_state(gs)
        prince.start_turn()  # Assess threat, plan actions
        action = prince.act(observation)  # Call repeatedly until turn ends
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

        # ── Internal state ────────────────────────────────────────
        # Relationships: suit → "unaligned" | "friend" | "conspirator"
        self.relationships: dict[Suit, str] = {
            s: "unaligned" for s in Suit
        }

        # Tactics: adds/subtracts attack dice in campaigns (-1 to +3)
        self.tactics: int = 0
        self._tactics_steps: int = 0  # total times tactics increased

        # Caution: threshold added to Ready to Fight check (0+)
        self.caution: int = 0

        # Threat tracking
        self._current_threat: Optional[str] = None
        self._threat_player: Optional[int] = None
        self._previous_threat: Optional[str] = None
        self._is_first_turn: bool = True

        # Turn state
        self._game_state: Optional[GameState] = None
        self._action_queue: list[str] = []
        self._actions_taken: int = 0
        self._max_actions: int = 2
        self._has_played_card: bool = False
        self._has_searched: bool = False
        self._search_discard_queue: list[int] = []  # card indices to discard
        self._search_play_idx: Optional[int] = None  # card index to play

    def reset(self):
        """Reset all internal state for a new game."""
        self.relationships = {s: "unaligned" for s in Suit}
        self.tactics = 0
        self._tactics_steps = 0
        self.caution = 0
        self._current_threat = None
        self._threat_player = None
        self._previous_threat = None
        self._is_first_turn = True
        self._game_state = None
        self._action_queue = []
        self._actions_taken = 0
        self._max_actions = 2
        self._has_played_card = False
        self._has_searched = False
        self._search_discard_queue = []
        self._search_play_idx = None

    def set_game_state(self, gs: 'GameState'):
        """Provide direct game state access for this turn."""
        self._game_state = gs

    def start_turn(self):
        """Begin the Prince's turn: assess threat, plan actions."""
        gs = self._game_state
        if gs is None:
            return

        self._actions_taken = 0
        self._has_played_card = False
        self._has_searched = False
        self._search_discard_queue = []
        self._search_play_idx = None

        # Step 1: Assess Threat (skip on first turn)
        if self._is_first_turn:
            self._is_first_turn = False
        else:
            self._previous_threat = self._current_threat
            threat_type, threat_player = self._assess_threat(gs)
            self._current_threat = threat_type
            self._threat_player = threat_player

        # Compute number of actions from relationships
        self._max_actions = self._compute_num_actions()

        # Step 3: Plan actions from Mind flowchart
        self._action_queue = self._plan_actions(gs)

    def act(self, observation: dict) -> int:
        """Select the next action ID given the observation."""
        mask = observation["action_mask"]
        gs = self._game_state
        legal = np.where(np.array(mask) > 0.5)[0]

        if len(legal) == 0:
            return 43  # END_ACT_PHASE fallback

        if gs is None:
            return int(np.random.choice(legal))

        # Handle compound states first
        if gs.compound_state is not None:
            return self._handle_compound(gs, mask, legal)

        # Step 2: Play One Card (search to draw cards)
        if not self._has_searched and not self._has_played_card:
            if 8 in legal:  # Search deck
                self._has_searched = True
                return 8
            # If can't search, skip card play
            self._has_played_card = True

        # Step 3: Take Actions from queue
        return self._handle_act_phase(gs, mask, legal)

    # ── Threat Assessment ────────────────────────────────────────

    def _assess_threat(self, gs: 'GameState') -> tuple[Optional[str], Optional[int]]:
        """Determine the current threat, checked in priority order."""
        from oath.engine.win_conditions import _check_successor_goal

        # 1. Does a Citizen meet the Successor goal?
        for i, p in enumerate(gs.players):
            if i == 0:
                continue  # Skip Chancellor
            if p.role == Role.CITIZEN:
                if _check_successor_goal(gs, i):
                    return (QUADRANT_SUCCESSOR, i)

        # 2. Is an Exile the Oathkeeper or Usurper?
        if gs.oathkeeper_holder is not None and gs.oathkeeper_holder != 0:
            holder = gs.players[gs.oathkeeper_holder]
            if holder.role == Role.EXILE:
                return (QUADRANT_OATHKEEPER, gs.oathkeeper_holder)

        # 3. Has an Exile completed/revealed a Vision?
        for i, p in enumerate(gs.players):
            if i == 0:
                continue
            if p.role in (Role.EXILE, Role.CITIZEN) and p.revealed_vision is not None:
                vision_id = p.revealed_vision
                # Map vision to appropriate quadrant
                if vision_id == 222:  # Faith → Darkest Secret
                    return (QUADRANT_DS, i)
                elif vision_id == 223:  # Rebellion → People's Favor
                    return (QUADRANT_PF, i)
                elif vision_id == 221:  # Conquest → sites
                    return (QUADRANT_SUCCESSOR, i)
                elif vision_id == 224:  # Sanctuary → relics
                    return (QUADRANT_OATHKEEPER, i)
                elif vision_id == 225:  # Conspiracy → secrets/DS
                    return (QUADRANT_DS, i)
                else:
                    return (QUADRANT_PF, i)

        return (None, None)

    # ── Relationships & Action Count ─────────────────────────────

    def _compute_num_actions(self) -> int:
        """Number of actions = 2 + non-unaligned relationships (cap 5)."""
        non_unaligned = sum(1 for v in self.relationships.values() if v != "unaligned")
        return min(5, 2 + non_unaligned)

    def _get_quadrant_suit_preference(self) -> str:
        """Get whether this quadrant prefers Friends or Conspirators."""
        if self._current_threat in (QUADRANT_SUCCESSOR, QUADRANT_PF):
            return "friend"
        elif self._current_threat in (QUADRANT_OATHKEEPER, QUADRANT_DS):
            return "conspirator"
        return "friend"  # default

    def _advance_relationship(self, suit: Suit):
        """Advance a suit's relationship marker toward Friend or Conspirator."""
        preference = self._get_quadrant_suit_preference()
        current = self.relationships[suit]
        if current == "unaligned":
            self.relationships[suit] = preference

    # ── Card Play (Step 2) ───────────────────────────────────────

    def _pick_card_to_play(self, gs: 'GameState', drawn_cards: list[int]) -> tuple[Optional[int], list[int]]:
        """Choose which drawn card to play and which to discard.

        Returns (play_index, discard_indices).
        The card matching the current quadrant's preferred suit is played.
        """
        preference = self._get_quadrant_suit_preference()

        # Find suits that are Friends or Conspirators
        preferred_suits = set()
        for suit, rel in self.relationships.items():
            if rel == preference:
                preferred_suits.add(suit)

        # Try to find a card matching a preferred suit (earliest/leftmost)
        play_idx = None
        for i, card_id in enumerate(drawn_cards):
            card_data = get_card(card_id)
            if card_data.is_vision:
                continue  # Don't play visions
            if card_data.suit in preferred_suits:
                play_idx = i
                break

        # If no preferred suit match, play the first non-vision card
        if play_idx is None:
            for i, card_id in enumerate(drawn_cards):
                card_data = get_card(card_id)
                if not card_data.is_vision:
                    play_idx = i
                    break

        discard_indices = [i for i in range(len(drawn_cards)) if i != play_idx]
        return play_idx, discard_indices

    def _update_tactics_for_drawn_cards(self, gs: 'GameState', drawn_cards: list[int]):
        """For each battle plan revealed, increase Tactics."""
        from oath.cards.effects import get_battle_plan_effects
        for card_id in drawn_cards:
            effects = get_battle_plan_effects(card_id)
            if effects:
                self._tactics_steps += 1
                if self.tactics < 3:
                    self.tactics += 1
                elif self._tactics_steps == 1 and self.tactics == -1:
                    self.tactics = 0
                # At 3rd, 5th, 6th step, decrease caution
                if self._tactics_steps in _TACTICS_CAUTION_THRESHOLDS:
                    self.caution = max(0, self.caution - 1)

    # ── Mind Flowchart (Step 3) ──────────────────────────────────

    def _plan_actions(self, gs: 'GameState') -> list[str]:
        """Generate an action queue from the Mind flowchart."""
        prince = gs.players[0]

        if self._current_threat == QUADRANT_SUCCESSOR:
            return self._plan_successor_response(gs, prince)
        elif self._current_threat == QUADRANT_OATHKEEPER:
            return self._plan_oathkeeper_response(gs, prince)
        elif self._current_threat == QUADRANT_DS:
            return self._plan_ds_response(gs, prince)
        elif self._current_threat == QUADRANT_PF:
            return self._plan_pf_response(gs, prince)
        else:
            return self._plan_default(gs, prince)

    def _plan_default(self, gs: 'GameState', prince) -> list[str]:
        """No threat: muster, trade, travel to sites with resources."""
        actions = []
        # Travel to site with most favor+secrets available
        best_site = self._find_site_most_resources(gs)
        if best_site is not None and best_site != prince.pawn_site:
            actions.append(f"travel:{best_site}")
        actions.append("muster")
        actions.append("trade")
        actions.append("muster")
        return actions

    def _plan_successor_response(self, gs: 'GameState', prince) -> list[str]:
        """Top-Left: Citizen meets successor goal → campaign for sites."""
        actions = []
        my_sites = gs.count_sites_ruled(0)
        threat_sites = gs.count_sites_ruled(self._threat_player) if self._threat_player else 0

        if my_sites >= threat_sites and my_sites > 0:
            # Prince rules most sites → campaign to defend/expand
            target_site = self._find_rival_weakest_site(gs)
            if target_site is not None:
                if self._is_ready_to_fight(gs, target_site):
                    if target_site != prince.pawn_site:
                        actions.append(f"travel:{target_site}")
                    actions.append(f"campaign_site:{target_site}")
                else:
                    actions.append("muster")
                    actions.append("muster")
        else:
            # Need more sites → travel to resource-rich site, muster
            best_site = self._find_site_most_resources(gs)
            if best_site is not None and best_site != prince.pawn_site:
                actions.append(f"travel:{best_site}")
            actions.append("muster")
            actions.append("trade")

        return actions

    def _plan_oathkeeper_response(self, gs: 'GameState', prince) -> list[str]:
        """Top-Right: Exile is Oathkeeper → campaign for relics or reclaim title."""
        actions = []
        threat = self._threat_player

        if threat is not None:
            # Campaign the oathkeeper to reclaim title
            threat_site = gs.players[threat].pawn_site
            if self._is_ready_to_fight(gs, threat_site):
                if threat_site != prince.pawn_site:
                    actions.append(f"travel:{threat_site}")
                actions.append(f"campaign_player:{threat}")
            else:
                actions.append("muster")
                actions.append("muster")

        # Also try to recover relics
        relic_site = self._find_site_with_relic(gs)
        if relic_site is not None:
            if relic_site != prince.pawn_site:
                actions.append(f"travel:{relic_site}")
            actions.append("recover_relic")

        return actions

    def _plan_ds_response(self, gs: 'GameState', prince) -> list[str]:
        """Bottom-Left: Threat via Darkest Secret → recover or defend DS."""
        actions = []

        if gs.darkest_secret_holder == 0:
            # Prince holds DS → campaign the threat player
            threat = self._threat_player
            if threat is not None:
                threat_site = gs.players[threat].pawn_site
                if self._is_ready_to_fight(gs, threat_site):
                    if threat_site != prince.pawn_site:
                        actions.append(f"travel:{threat_site}")
                    actions.append(f"campaign_player:{threat}")
                else:
                    actions.append("muster")
        else:
            # Need to recover DS
            ds_holder = gs.darkest_secret_holder
            if ds_holder is not None:
                holder_site = gs.players[ds_holder].pawn_site
                if prince.secrets > gs.darkest_secret_tokens:
                    # Can recover → travel and recover
                    if holder_site != prince.pawn_site:
                        actions.append(f"travel:{holder_site}")
                    actions.append("recover_ds")
                else:
                    # Need more secrets → trade for secrets
                    actions.append("trade_secrets")
                    actions.append("trade_secrets")
            else:
                # DS is unclaimed → recover it
                actions.append("recover_ds")

        return actions

    def _plan_pf_response(self, gs: 'GameState', prince) -> list[str]:
        """Bottom-Right: Threat via People's Favor → recover or defend PF."""
        actions = []

        if gs.peoples_favor_holder == 0:
            # Prince holds PF → campaign the threat player
            threat = self._threat_player
            if threat is not None:
                threat_site = gs.players[threat].pawn_site
                if self._is_ready_to_fight(gs, threat_site):
                    if threat_site != prince.pawn_site:
                        actions.append(f"travel:{threat_site}")
                    actions.append(f"campaign_player:{threat}")
                else:
                    actions.append("muster")
        else:
            # Need to recover PF
            pf_holder = gs.peoples_favor_holder
            if pf_holder is not None:
                if prince.favor > gs.peoples_favor_tokens:
                    # Can recover → travel and recover
                    holder_site = gs.players[pf_holder].pawn_site
                    if holder_site != prince.pawn_site:
                        actions.append(f"travel:{holder_site}")
                    actions.append("recover_pf")
                else:
                    # Need more favor → trade for favor
                    actions.append("trade_favor")
                    actions.append("trade_favor")
            else:
                actions.append("recover_pf")

        return actions

    # ── Site Selection Helpers ───────────────────────────────────

    def _find_site_most_resources(self, gs: 'GameState') -> Optional[int]:
        """Find the faceup site with most total favor + secrets."""
        best = None
        best_val = -1
        for i in range(MAX_SITES):
            site = gs.sites[i]
            if not site.is_faceup:
                continue
            total = site.site_favor + site.site_secrets
            for slot in range(site.capacity):
                total += site.card_favor[slot] + site.card_secrets[slot]
            if total > best_val:
                best_val = total
                best = i
        return best

    def _find_rival_weakest_site(self, gs: 'GameState') -> Optional[int]:
        """Find a site ruled by the player with most sites, that has fewest warbands."""
        # Find player who rules most sites (excluding Prince)
        max_sites = 0
        rival = None
        for i in range(1, gs.num_players):
            count = gs.count_sites_ruled(i)
            if count > max_sites:
                max_sites = count
                rival = i

        if rival is None:
            return None

        # Find that rival's site with fewest warbands
        best_site = None
        best_warbands = float('inf')
        for i in range(MAX_SITES):
            site = gs.sites[i]
            if site.ruling_player == rival and site.is_faceup:
                if site.warbands < best_warbands:
                    best_warbands = site.warbands
                    best_site = i

        return best_site

    def _find_site_with_relic(self, gs: 'GameState') -> Optional[int]:
        """Find a faceup site with relics, preferring Cradle > Provinces > Hinterland."""
        for region in [Region.CRADLE, Region.PROVINCES, Region.HINTERLAND]:
            for i in range(MAX_SITES):
                site = gs.sites[i]
                if site.is_faceup and site.region == region and len(site.relics) > 0:
                    return i
        return None

    def _find_unexplored_site(self, gs: 'GameState') -> Optional[int]:
        """Find a facedown site to explore."""
        for i in range(MAX_SITES):
            if not gs.sites[i].is_faceup:
                return i
        return None

    # ── Ready to Fight ───────────────────────────────────────────

    def _is_ready_to_fight(self, gs: 'GameState', target_site: int) -> bool:
        """Check if Prince has enough warbands to campaign at target site."""
        prince = gs.players[0]
        site = gs.sites[target_site]

        # Defender's warbands at site
        defender_warbands = site.warbands

        # Site defense dice
        site_card = get_card(site.site_id)
        defense_dice = site_card.defense

        # Threshold: defender warbands + defense dice + caution
        threshold = defender_warbands + defense_dice + self.caution

        return prince.warbands_board > threshold

    # ── Act Phase Action Execution ───────────────────────────────

    def _handle_act_phase(self, gs: 'GameState', mask, legal) -> int:
        """Execute the next action from the queue or end turn."""
        prince = gs.players[0]

        # Process action queue
        while self._action_queue and self._actions_taken < self._max_actions:
            action_str = self._action_queue.pop(0)
            action_id = self._resolve_action(gs, action_str, mask, legal)
            if action_id is not None:
                self._actions_taken += 1
                return action_id
            # Action not legal, skip it (doesn't count toward action limit)

        # Queue exhausted or max actions reached → end act phase
        if 43 in legal:
            return 43

        # Fallback: random legal action
        return int(np.random.choice(legal))

    def _resolve_action(self, gs: 'GameState', action_str: str, mask, legal) -> Optional[int]:
        """Convert a high-level action string to an action ID, or None if illegal."""
        prince = gs.players[0]

        if action_str.startswith("travel:"):
            site_idx = int(action_str.split(":")[1])
            if site_idx in legal:
                return site_idx
            return None

        elif action_str == "muster":
            # Muster on first legal slot
            for slot in range(3):
                aid = 10 + slot
                if aid in legal:
                    return aid
            return None

        elif action_str == "trade" or action_str == "trade_favor":
            # Trade for favor on first legal slot
            for slot in range(3):
                aid = 13 + slot
                if aid in legal:
                    return aid
            return None

        elif action_str == "trade_secrets":
            # Trade for secrets on first legal slot
            for slot in range(3):
                aid = 16 + slot
                if aid in legal:
                    return aid
            return None

        elif action_str == "recover_relic":
            # Recover first legal relic
            for slot in range(3):
                aid = 19 + slot
                if aid in legal:
                    return aid
            return None

        elif action_str == "recover_pf":
            if 22 in legal:
                return 22
            return None

        elif action_str == "recover_ds":
            if 23 in legal:
                return 23
            return None

        elif action_str.startswith("campaign_player:"):
            target = int(action_str.split(":")[1])
            # Convert absolute target to relative
            rel = (target - 0) % gs.num_players  # Prince is always player 0
            if rel == 0:
                return None
            aid = 24 + rel - 1
            if aid in legal:
                return aid
            return None

        elif action_str.startswith("campaign_site:"):
            target_site = int(action_str.split(":")[1])
            # Find the ruling player at that site to campaign
            ruler = gs.sites[target_site].ruling_player
            if ruler is not None and ruler != 0:
                rel = ruler % gs.num_players
                aid = 24 + rel - 1
                if aid in legal:
                    return aid
            return None

        elif action_str == "search":
            if 8 in legal:
                return 8
            return None

        return None

    # ── Compound State Handlers ──────────────────────────────────

    def _handle_compound(self, gs: 'GameState', mask, legal) -> int:
        """Handle compound state actions."""
        cs = gs.compound_state
        if cs is None:
            return int(np.random.choice(legal))

        if cs.state_type == CompoundStateType.SEARCH_CHOOSE:
            return self._handle_search_choose(gs, cs, mask, legal)
        elif cs.state_type == CompoundStateType.CAMPAIGN_TARGETS:
            return self._handle_campaign_targets(gs, cs, mask, legal)
        elif cs.state_type == CompoundStateType.CAMPAIGN_BATTLE:
            return self._handle_campaign_battle(gs, cs, mask, legal)
        elif cs.state_type == CompoundStateType.CAMPAIGN_SACRIFICE:
            return self._handle_campaign_sacrifice(gs, cs, mask, legal)
        elif cs.state_type == CompoundStateType.RELIQUARY_CHOOSE:
            # Pick first legal reliquary slot
            for slot in range(4):
                if (52 + slot) in legal:
                    return 52 + slot
            return int(np.random.choice(legal))
        elif cs.state_type == CompoundStateType.CITIZENSHIP_RESPONSE:
            # Prince doesn't respond to citizenship (always decline as Chancellor)
            if 50 in legal:
                return 50  # Decline
            return int(np.random.choice(legal))

        return int(np.random.choice(legal))

    def _handle_search_choose(self, gs: 'GameState', cs, mask, legal) -> int:
        """Handle SEARCH_CHOOSE: play one card, discard the rest."""
        drawn = cs.drawn_cards
        remaining = cs.cards_remaining

        # First call: decide which card to play and which to discard
        if self._search_play_idx is None and not self._search_discard_queue:
            # Update tactics for battle plans in drawn cards
            self._update_tactics_for_drawn_cards(gs, drawn)

            play_idx, discard_indices = self._pick_card_to_play(gs, drawn)
            if play_idx is not None:
                self._search_play_idx = play_idx
                # Advance relationship for the played card's suit
                card_data = get_card(drawn[play_idx])
                if card_data.suit is not None:
                    self._advance_relationship(card_data.suit)
            self._search_discard_queue = [i for i in discard_indices if i < len(remaining) and remaining[i]]

        # Discard cards first (before playing, to clear the queue)
        while self._search_discard_queue:
            idx = self._search_discard_queue[0]
            aid = 81 + idx
            if aid in legal:
                self._search_discard_queue.pop(0)
                return aid
            else:
                self._search_discard_queue.pop(0)

        # Play the chosen card to a site
        if self._search_play_idx is not None:
            idx = self._search_play_idx
            card_id = drawn[idx]
            card_data = get_card(card_id)

            # Try to play to site (prefer Cradle → Provinces → Hinterland)
            play_to_site = 66 + idx * 3 + 0  # site destination
            if play_to_site in legal and card_data.restriction != CardRestriction.ADVISER_ONLY:
                self._search_play_idx = None
                self._has_played_card = True
                return play_to_site

            # If can't play to site, play as faceup adviser
            play_adviser_up = 66 + idx * 3 + 1
            if play_adviser_up in legal:
                self._search_play_idx = None
                self._has_played_card = True
                return play_adviser_up

            # If can't play at all, discard it (Prince gains 3 warbands conceptually)
            discard_aid = 81 + idx
            if discard_aid in legal:
                self._search_play_idx = None
                self._has_played_card = True
                return discard_aid

        # Fallback: discard any remaining card
        for i in range(5):
            if i < len(cs.cards_remaining) and cs.cards_remaining[i]:
                aid = 81 + i
                if aid in legal:
                    self._has_played_card = True
                    return aid

        return int(np.random.choice(legal))

    def _handle_campaign_targets(self, gs: 'GameState', cs, mask, legal) -> int:
        """Handle CAMPAIGN_TARGET: target sites/relics following Prince rules."""
        prince = gs.players[0]
        defender = cs.campaign_defender

        if defender is None:
            if 87 in legal:
                return 87  # Done targets
            return int(np.random.choice(legal))

        # If we have targets already, check if we should add more or finish
        if cs.campaign_targets:
            # Target as many sites as possible while Ready to Fight
            # Check if we can add more targets
            can_add_more = False
            for site_idx in range(MAX_SITES):
                aid = 88 + site_idx
                if aid in legal:
                    # Check if adding this site keeps us Ready to Fight
                    site = gs.sites[site_idx]
                    current_defense = self._estimate_current_defense(gs, cs)
                    new_defense = current_defense + site.warbands + get_card(site.site_id).defense
                    if prince.warbands_board > new_defense + self.caution:
                        can_add_more = True
                        return aid

            # Done adding targets
            if 87 in legal:
                return 87
            return int(np.random.choice(legal))

        # First target: pick site with fewest warbands ruled by defender
        best_site = None
        best_warbands = float('inf')
        for site_idx in range(MAX_SITES):
            aid = 88 + site_idx
            if aid in legal:
                site = gs.sites[site_idx]
                if site.warbands < best_warbands:
                    best_warbands = site.warbands
                    best_site = site_idx

        if best_site is not None:
            return 88 + best_site

        # Try targeting relics
        for slot in range(5):
            aid = 96 + slot
            if aid in legal:
                return aid

        # Done
        if 87 in legal:
            return 87

        return int(np.random.choice(legal))

    def _handle_campaign_battle(self, gs: 'GameState', cs, mask, legal) -> int:
        """Handle CAMPAIGN_BATTLE: use free battle plans (Limited Powers)."""
        # Try each faceup adviser's battle plan
        prince = gs.players[0]
        from oath.cards.effects import get_battle_plan_effects
        for slot in range(MAX_ADVISERS):
            aid = 56 + slot
            if aid in legal:
                card_id = prince.advisers[slot]
                if card_id is not None:
                    effects = get_battle_plan_effects(card_id)
                    if effects:
                        # Limited Powers: use it (no cost check needed since
                        # battle plans don't have costs in the action system)
                        return aid

        # No battle plan → skip
        if 59 in legal:
            return 59

        return int(np.random.choice(legal))

    def _handle_campaign_sacrifice(self, gs: 'GameState', cs, mask, legal) -> int:
        """Handle CAMPAIGN_SACRIFICE: always sacrifice if would make victorious."""
        deficit = cs.campaign_defense_result - cs.campaign_attack_result
        if deficit <= 0:
            # Already winning, sacrifice 0
            if 60 in legal:
                return 60
            return int(np.random.choice(legal))

        # Sacrifice exactly enough to win
        sacrifice = deficit
        aid = 60 + sacrifice
        if aid in legal:
            return aid

        # Can't sacrifice enough → sacrifice 0
        if 60 in legal:
            return 60

        return int(np.random.choice(legal))

    def _estimate_current_defense(self, gs: 'GameState', cs) -> int:
        """Estimate current defense pool from existing campaign targets."""
        defense = 0
        for target in cs.campaign_targets:
            if target.startswith("site:"):
                site_idx = int(target.split(":")[1])
                site = gs.sites[site_idx]
                defense += site.warbands
                defense += get_card(site.site_id).defense
        return defense

    def on_campaign_defeat(self):
        """Called when the Prince loses a campaign as attacker."""
        self.caution += 1

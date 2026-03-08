"""PettingZoo AEC environment for Oath simulator."""

from __future__ import annotations

import copy
import functools
from typing import Optional

import numpy as np
from gymnasium import spaces

from oath.enums import (
    CompoundStateType, Phase, NUM_ACTIONS, NUM_CARD_IDS, MAX_SITES,
    MAX_CARDS_PER_SITE, MAX_ADVISERS, MAX_PLAYERS,
)
from oath.state.game_state import GameState
from oath.engine.game import (
    create_initial_state, advance_turn, start_act_phase, do_rest_phase,
    do_wake_phase,
)
from oath.engine.win_conditions import check_start_of_turn_wins
from oath.env.action_decoder import ActionDecoder, DecodedAction
from oath.env.observation import encode_observation, OBS_SIZE
from oath.env.reward import compute_reward


class OathEnv:
    """PettingZoo-compatible AEC environment for Oath.

    Implements the core AEC API without inheriting from PettingZoo
    to avoid hard dependency issues. Compatible with PettingZoo wrappers.
    """

    metadata = {"render_modes": ["human", "ansi"], "name": "oath_v0"}

    def __init__(
        self,
        num_players: int = 4,
        render_mode: Optional[str] = None,
        seed: Optional[int] = None,
        first_game: bool = True,
        clockwork_prince: bool = False,
        chronicle_mode: bool = False,
    ):
        self.num_players = num_players
        self.render_mode = render_mode
        self._seed = seed
        self._first_game = first_game
        self._clockwork_prince = clockwork_prince
        self._chronicle_mode = chronicle_mode
        self._chronicle_state = None  # ChronicleState persists between resets
        self._prince_agent = None

        if clockwork_prince:
            from oath.agents.clockwork_prince import ClockworkPrinceAgent
            self._prince_agent = ClockworkPrinceAgent(seed=seed)

        self.possible_agents = [f"player_{i}" for i in range(num_players)]
        self.agents: list[str] = []
        self.action_decoder = ActionDecoder()

        # Will be set on reset
        self.game_state: Optional[GameState] = None
        self._agent_selector: Optional[_AgentSelector] = None
        self.agent_selection: str = ""

        # Per-agent accumulators
        self.rewards: dict[str, float] = {}
        self._cumulative_rewards: dict[str, float] = {}
        self.terminations: dict[str, bool] = {}
        self.truncations: dict[str, bool] = {}
        self.infos: dict[str, dict] = {}

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent: str) -> spaces.Dict:
        return spaces.Dict({
            "observation": spaces.Box(
                low=-1.0, high=1.0, shape=(OBS_SIZE,), dtype=np.float32
            ),
            "action_mask": spaces.Box(
                low=0, high=1, shape=(NUM_ACTIONS,), dtype=np.int8
            ),
        })

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent: str) -> spaces.Discrete:
        return spaces.Discrete(NUM_ACTIONS)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        """Reset the environment to a new game.

        In chronicle_mode, if a previous game ended, the chronicle is applied
        automatically and the next game uses the resulting ChronicleState.
        """
        if seed is not None:
            self._seed = seed

        # Apply chronicle from previous game if in chronicle mode
        if (self._chronicle_mode and self.game_state is not None
                and self.game_state.is_game_over):
            from oath.engine.chronicle import apply_chronicle
            self._chronicle_state = apply_chronicle(
                self.game_state,
                prev_chronicle=self._chronicle_state,
            )

        self.game_state = create_initial_state(
            num_players=self.num_players,
            seed=self._seed,
            first_game=self._first_game and self._chronicle_state is None,
            chronicle=self._chronicle_state,
        )

        self.agents = list(self.possible_agents)
        self._agent_selector = _AgentSelector(self.agents)
        self.agent_selection = self._agent_selector.reset()

        # Initialize per-agent state
        for agent in self.agents:
            self.rewards[agent] = 0.0
            self._cumulative_rewards[agent] = 0.0
            self.terminations[agent] = False
            self.truncations[agent] = False
            self.infos[agent] = {}

        # Reset Clockwork Prince if active
        if self._prince_agent is not None:
            self._prince_agent.reset()

        # Auto-advance through wake phase for first player
        # (also auto-plays Clockwork Prince if active)
        self._auto_advance_phases()

        # Update agent selection to match current player after auto-advance
        if self.game_state and not self.game_state.is_game_over:
            self.agent_selection = f"player_{self.game_state.current_player_index}"

    def step(self, action: Optional[int]):
        """Apply an action for the current agent."""
        gs = self.game_state
        if gs is None:
            raise RuntimeError("Must call reset() before step()")

        agent = self.agent_selection

        # Handle terminated/truncated agents
        if self.terminations.get(agent, False) or self.truncations.get(agent, False):
            self._was_dead_step(action)
            return

        if action is None:
            # No-op for dead agents
            self._advance_agent()
            return

        player_idx = int(agent.split("_")[1])

        # Save state for reward computation
        prev_state = copy.deepcopy(gs)

        # Decode and apply action
        decoded = self.action_decoder.decode(action)
        self._apply_action(gs, player_idx, decoded)

        # Compute reward
        reward = compute_reward(prev_state, decoded, gs, player_idx)
        self.rewards[agent] = reward
        self._cumulative_rewards[agent] += reward

        # Check if game is over
        if gs.is_game_over:
            self._handle_game_over()
            return

        # Check if compound action continues
        if gs.in_compound_action:
            # Citizenship response must be handled by the target, not the offerer
            if (gs.compound_state.state_type == CompoundStateType.CITIZENSHIP_RESPONSE and
                    gs.compound_state.citizenship_target is not None and
                    gs.compound_state.citizenship_target != player_idx):
                target_agent = f"player_{gs.compound_state.citizenship_target}"
                if target_agent in self.agents:
                    self.agent_selection = target_agent
                    return
            # Otherwise same player continues the compound action
            return

        # After citizenship response resolved, return control to the current player
        if player_idx != gs.current_player_index:
            current_agent = f"player_{gs.current_player_index}"
            if current_agent in self.agents:
                self.agent_selection = current_agent
                return

        # Check if act phase ended
        if gs.phase == Phase.REST:
            do_rest_phase(gs)
            advance_turn(gs)

            if gs.is_game_over:
                self._handle_game_over()
                return

            self._auto_advance_phases()
            self._advance_agent()

    def observe(self, agent: str) -> dict:
        """Get observation for the given agent."""
        if self.game_state is None:
            return {
                "observation": np.zeros(OBS_SIZE, dtype=np.float32),
                "action_mask": np.zeros(NUM_ACTIONS, dtype=np.float32),
            }

        player_idx = int(agent.split("_")[1])
        return encode_observation(self.game_state, player_idx)

    def last(self, observe: bool = True):
        """Get the last observation, reward, termination, truncation, info."""
        agent = self.agent_selection
        obs = self.observe(agent) if observe else None
        return (
            obs,
            self._cumulative_rewards.get(agent, 0.0),
            self.terminations.get(agent, False),
            self.truncations.get(agent, False),
            self.infos.get(agent, {}),
        )

    def agent_iter(self, max_iter: int = 2**63):
        """Iterate over agents until game is over."""
        count = 0
        while self.agents and count < max_iter:
            yield self.agent_selection
            count += 1

    def render(self):
        """Render the current state."""
        if self.game_state is None:
            return "No game in progress"

        gs = self.game_state
        lines = [
            f"Round {gs.round_number}, Phase: {gs.phase.name}",
            f"Current player: {gs.current_player_index}",
            f"Oath: {gs.oath_goal.name}",
            "",
        ]

        for i, player in enumerate(gs.players):
            marker = ">>>" if i == gs.current_player_index else "   "
            lines.append(
                f"{marker} Player {i} ({player.role.name}): "
                f"site={player.pawn_site} supply={player.supply} "
                f"favor={player.favor} secrets={player.secrets} "
                f"warbands={player.warbands_bank}+{player.warbands_board}"
            )

        if self.render_mode == "human":
            print("\n".join(lines))

        return "\n".join(lines)

    def _apply_action(self, gs: GameState, player_idx: int, decoded: DecodedAction):
        """Apply a decoded action to the game state."""
        from oath.enums import ActionType
        from oath.engine.actions import (
            execute_travel, execute_muster, execute_trade_favor,
            execute_trade_secrets, execute_search, execute_search_play,
            execute_search_discard, execute_recover_relic,
            execute_recover_peoples_favor, execute_recover_darkest_secret,
            execute_flip_adviser, execute_use_card_action,
            execute_end_act_phase, execute_offer_citizenship,
            execute_reliquary_choose, execute_accept_citizenship,
            execute_decline_citizenship, execute_self_exile,
        )
        from oath.engine.campaign import (
            execute_campaign_declare, execute_campaign_target_site,
            execute_campaign_target_relic, execute_campaign_target_pawn,
            execute_campaign_done_targets, execute_campaign_battle_plan,
            execute_campaign_no_battle, execute_campaign_sacrifice,
        )

        at = decoded.action_type

        if at == ActionType.TRAVEL:
            execute_travel(gs, player_idx, decoded.site_index)
        elif at == ActionType.SEARCH:
            execute_search(gs, player_idx, decoded.search_destination)
        elif at == ActionType.MUSTER:
            execute_muster(gs, player_idx, decoded.card_slot)
        elif at == ActionType.TRADE_FAVOR:
            execute_trade_favor(gs, player_idx, decoded.card_slot)
        elif at == ActionType.TRADE_SECRETS:
            execute_trade_secrets(gs, player_idx, decoded.card_slot)
        elif at == ActionType.RECOVER:
            execute_recover_relic(gs, player_idx, decoded.target_relic_slot)
        elif at == ActionType.RECOVER_PEOPLES_FAVOR:
            execute_recover_peoples_favor(gs, player_idx)
        elif at == ActionType.RECOVER_DARKEST_SECRET:
            execute_recover_darkest_secret(gs, player_idx)
        elif at == ActionType.CAMPAIGN_DECLARE:
            # Convert relative player to absolute
            abs_target = (player_idx + decoded.target_player) % gs.num_players
            execute_campaign_declare(gs, player_idx, abs_target)
        elif at == ActionType.MINOR_FLIP_ADVISER:
            execute_flip_adviser(gs, player_idx, decoded.card_slot)
        elif at == ActionType.MINOR_USE_ACTION:
            execute_use_card_action(gs, player_idx, decoded.card_slot)
        elif at == ActionType.END_ACT_PHASE:
            execute_end_act_phase(gs, player_idx)
        elif at == ActionType.OFFER_CITIZENSHIP:
            abs_target = (player_idx + decoded.target_player) % gs.num_players
            execute_offer_citizenship(gs, player_idx, abs_target)
        elif at == ActionType.RELIQUARY_CHOOSE:
            execute_reliquary_choose(gs, player_idx, decoded.card_slot)
        elif at == ActionType.ACCEPT_CITIZENSHIP:
            execute_accept_citizenship(gs, player_idx)
        elif at == ActionType.DECLINE_CITIZENSHIP:
            execute_decline_citizenship(gs, player_idx)
        elif at == ActionType.SELF_EXILE:
            execute_self_exile(gs, player_idx)
        elif at == ActionType.CAMPAIGN_BATTLE_PLAN:
            execute_campaign_battle_plan(gs, player_idx, decoded.card_slot)
        elif at == ActionType.CAMPAIGN_NO_BATTLE:
            execute_campaign_no_battle(gs, player_idx)
        elif at == ActionType.CAMPAIGN_SACRIFICE:
            execute_campaign_sacrifice(gs, player_idx, decoded.sacrifice_count)
        elif at == ActionType.SEARCH_PLAY:
            execute_search_play(gs, player_idx,
                              decoded.search_card_index, decoded.search_destination)
        elif at == ActionType.SEARCH_DISCARD:
            execute_search_discard(gs, player_idx, decoded.search_card_index)
        elif at == ActionType.CAMPAIGN_DONE_TARGETS:
            execute_campaign_done_targets(gs, player_idx)
        elif at == ActionType.CAMPAIGN_TARGET_SITE:
            execute_campaign_target_site(gs, player_idx, decoded.site_index)
        elif at == ActionType.CAMPAIGN_TARGET_RELIC:
            execute_campaign_target_relic(gs, player_idx, decoded.target_relic_slot)
        elif at == ActionType.CAMPAIGN_TARGET_PAWN:
            execute_campaign_target_pawn(gs, player_idx)
        elif at in (ActionType.COMM_SIGNAL, ActionType.COMM_TARGET):
            pass  # Communication is a no-op for now
        elif at in (ActionType.MINOR_WARBANDS, ActionType.MINOR_PEEK_RELIC,
                    ActionType.CAMPAIGN_ADD_TARGET):
            pass  # Stubs

    def _auto_advance_phases(self):
        """Auto-advance through wake phase to act phase.

        If Clockwork Prince is active and it's the Chancellor's turn,
        auto-play the entire turn so exile agents never see it.
        """
        gs = self.game_state
        if gs is None:
            return

        if gs.phase == Phase.WAKE:
            # Check start-of-turn wins
            winner = check_start_of_turn_wins(gs, gs.current_player_index)
            if winner is not None:
                gs.is_game_over = True
                gs.winner = winner
                self._handle_game_over()
                return
            do_wake_phase(gs)
            start_act_phase(gs)

        # If Clockwork Prince is active and it's Chancellor's turn, auto-play
        if (self._clockwork_prince and self._prince_agent is not None
                and gs.current_player_index == gs.chancellor_index
                and gs.phase == Phase.ACT
                and not gs.is_game_over):
            self._run_clockwork_prince()

    def _run_clockwork_prince(self):
        """Execute the Clockwork Prince's entire turn automatically."""
        gs = self.game_state
        chanc_idx = gs.chancellor_index
        chanc_agent = f"player_{chanc_idx}"
        prince = self._prince_agent
        prince.set_game_state(gs)
        prince.start_turn()

        max_steps = 100  # Safety limit to prevent infinite loops
        for _ in range(max_steps):
            if gs.is_game_over:
                self._handle_game_over()
                return

            # Check if Chancellor's turn ended (moved to REST or next player)
            if gs.phase == Phase.REST:
                break
            if gs.phase != Phase.ACT and not gs.in_compound_action:
                break

            obs = self.observe(chanc_agent)
            action = prince.act(obs)

            # Validate action is legal
            mask = obs["action_mask"]
            if mask[action] < 0.5:
                # Illegal action — end turn if possible
                if mask[43] > 0.5:
                    action = 43
                else:
                    # Pick first legal action as fallback
                    legal = np.where(np.array(mask) > 0.5)[0]
                    if len(legal) == 0:
                        break
                    action = int(legal[0])

            decoded = self.action_decoder.decode(action)
            self._apply_action(gs, chanc_idx, decoded)

        # Handle rest phase transition
        if gs.phase == Phase.REST and not gs.is_game_over:
            do_rest_phase(gs)
            advance_turn(gs)

            if gs.is_game_over:
                self._handle_game_over()
                return

            # Recursively advance phases (handles next player's wake,
            # or another Prince turn if round wraps)
            self._auto_advance_phases()

    def _advance_agent(self):
        """Advance to the next agent in turn order.

        When Clockwork Prince is active, player_0 is auto-played so we
        skip directly to the current (non-Chancellor) player.
        """
        gs = self.game_state
        if gs is None or self._agent_selector is None:
            return

        agent = f"player_{gs.current_player_index}"
        if agent in self.agents:
            self.agent_selection = agent

    def _handle_game_over(self):
        """Set all agents to terminated."""
        gs = self.game_state
        if gs is None:
            return

        for agent in self.agents:
            player_idx = int(agent.split("_")[1])
            self.terminations[agent] = True
            if gs.winner == player_idx:
                self.rewards[agent] = 1.0
            else:
                self.rewards[agent] = -1.0
            self._cumulative_rewards[agent] += self.rewards[agent]
            self.infos[agent]["winner"] = gs.winner
            self.infos[agent]["win_type"] = gs.win_type

        self.agents = []

    def _was_dead_step(self, action):
        """Handle step for terminated agent."""
        if self._agent_selector:
            self.agent_selection = self._agent_selector.next()


class _AgentSelector:
    """Simple agent selector that cycles through agents."""

    def __init__(self, agents: list[str]):
        self._agents = agents
        self._idx = 0

    def reset(self) -> str:
        self._idx = 0
        return self._agents[0]

    def next(self) -> str:
        self._idx = (self._idx + 1) % len(self._agents)
        return self._agents[self._idx]

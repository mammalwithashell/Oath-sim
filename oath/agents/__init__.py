"""Agent implementations for Oath simulator.

Available agents:
    RandomAgent: Uniform random baseline (picks any legal action).
    HeuristicAgent: Simple priority-based agent (search > muster > trade > travel).
    ClockworkPrinceAgent: Official Oath solo-play automa for the Chancellor (player 0).
        Implements the Clockwork Prince flowchart with threat assessment, Mind
        quadrants, and Ready to Fight calculation. Use with ``clockwork_prince=True``
        in OathEnv for automatic Chancellor play during exile RL training.
    HumanAgent: Interactive CLI agent that prompts for input.
"""

from oath.agents.clockwork_prince import ClockworkPrinceAgent
from oath.agents.human_agent import HumanAgent

__all__ = ["ClockworkPrinceAgent", "HumanAgent"]

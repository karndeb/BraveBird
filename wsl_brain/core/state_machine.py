from enum import Enum, auto
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Defines the lifecycle of the Agent using the State Pattern. 
# This prevents the agent from trying to "act" while it is still "observing".

class AgentState(Enum):
    IDLE = auto()          # Waiting for task
    PLANNING = auto()      # Generating workflow from trace/instruction
    OBSERVING = auto()     # Gathering visual/a11y data
    THINKING = auto()      # Reasoning about the next step
    ACTING = auto()        # Sending command to Sandbox
    VERIFYING = auto()     # Checking if action succeeded
    RECOVERING = auto()    # Rolling back snapshot after error
    FINISHED = auto()      # Task complete
    FAILED = auto()        # Task failed irrecoverably

class StateMachine:
    """
    Manages the lifecycle of the Agent S3 Controller.
    Enforces valid transitions to prevent race conditions.
    """

    def __init__(self):
        self._current_state = AgentState.IDLE
        self._history = []

    @property
    def current(self) -> AgentState:
        return self._current_state

    def transition_to(self, new_state: AgentState, reason: str = ""):
        """
        Transitions the agent to a new state if valid.
        
        Args:
            new_state: The target state.
            reason: Optional log message explaining the transition.
        """
        if new_state == self._current_state:
            return

        # Define invalid transitions here (simple circuit breaker)
        if self._current_state == AgentState.FAILED and new_state == AgentState.ACTING:
            logger.warning("⛔ Cannot switch from FAILED to ACTING without resetting.")
            return

        logger.info(f"🔄 State Transition: {self._current_state.name} -> {new_state.name} | {reason}")
        
        # Log history
        self._history.append({
            "from": self._current_state.name,
            "to": new_state.name,
            "reason": reason
        })
        
        self._current_state = new_state

    def is_terminal(self) -> bool:
        """Returns True if the agent has stopped working."""
        return self._current_state in [AgentState.FINISHED, AgentState.FAILED]
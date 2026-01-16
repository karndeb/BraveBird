import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# The Interface Contract. Defines strict requirements for any execution environment.

class SandboxCapabilities(BaseModel):
    """Defines what a specific sandbox implementation can do."""
    can_snapshot: bool = False
    can_run_code: bool = False
    can_browser_interact: bool = False
    os_type: str  # "linux" | "windows"

class SandboxEnv(ABC):
    """
    Abstract Base Class for all Execution Environments.
    Enforces a unified API for the Agent S3 Controller.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._is_active = False

    @property
    @abstractmethod
    def capabilities(self) -> SandboxCapabilities:
        """Returns the capabilities of this sandbox."""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Boots the environment (VM, Container, or Connection)."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Shuts down the environment and cleans up resources."""
        pass

    @abstractmethod
    async def get_screenshot(self) -> bytes:
        """
        Returns the current screen state as raw PNG bytes.
        Must handle retries and connection jitters.
        """
        pass

    @abstractmethod
    async def execute_mouse_action(self, action_type: str, x: int, y: int, button: str = "left") -> bool:
        """
        Executes a mouse event.
        action_type: "click", "dblclick", "move", "drag"
        """
        pass

    @abstractmethod
    async def execute_keyboard_action(self, text: str = None, keys: List[str] = None) -> bool:
        """
        Executes keyboard events.
        """
        pass

    @abstractmethod
    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Executes a shell/python command inside the sandbox.
        Returns: {'stdout': str, 'stderr': str, 'exit_code': int}
        """
        pass

    # --- Time Travel Interface ---

    @abstractmethod
    async def snapshot_state(self, tag: str) -> str:
        """
        Creates a checkpoint of the current system state (RAM + Disk).
        Returns: snapshot_id
        """
        pass

    @abstractmethod
    async def restore_state(self, snapshot_id: str) -> bool:
        """
        Reverts the system state to a specific snapshot.
        """
        pass
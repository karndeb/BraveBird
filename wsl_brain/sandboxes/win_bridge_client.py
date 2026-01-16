import logging
import aiohttp
from typing import Dict, Any, List

from wsl_brain.sandboxes.base import SandboxEnv, SandboxCapabilities

logger = logging.getLogger(__name__)

# The Production Client. Controls the host machine via the Bridge Server.


class WindowsBridgeSandbox(SandboxEnv):
    """
    Controls the Host Windows OS via the 'windows_host/core/bridge_server.py'.
    Used for production/recording mode.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Access host from WSL container
        self.api_url = config.get("bridge_url", "http://host.docker.internal:5050")

    @property
    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            can_snapshot=False,
            can_run_code=False, # Restricted for security on host
            can_browser_interact=True,
            os_type="windows"
        )

    async def start(self) -> bool:
        # Host is always running
        return True

    async def stop(self) -> bool:
        return True

    async def get_screenshot(self) -> bytes:
        # For the Bridge, we usually prefer the SHM Reader in the Perception Actor
        # This is a fallback HTTP method
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/screenshot") as resp:
                if resp.status == 200:
                    return await resp.read()
        return b""

    async def execute_mouse_action(self, action_type: str, x: int, y: int, button: str = "left") -> bool:
        payload = {"type": action_type, "x": x, "y": y, "button": button}
        return await self._post_action(payload)

    async def execute_keyboard_action(self, text: str = None, keys: List[str] = None) -> bool:
        payload = {"type": "type", "text": text, "keys": keys}
        return await self._post_action(payload)

    async def _post_action(self, payload: Dict) -> bool:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.api_url}/action", json=payload) as resp:
                    return resp.status == 200
            except Exception as e:
                logger.error(f"❌ [WinBridge] Connection failed: {e}")
                return False

    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        logger.error("⛔ [WinBridge] Code execution blocked on Host OS for security.")
        return {'stdout': '', 'stderr': 'Security Block', 'exit_code': 1}

    async def snapshot_state(self, tag: str) -> str:
        return ""

    async def restore_state(self, snapshot_id: str) -> bool:
        return False
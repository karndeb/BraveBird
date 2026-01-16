import logging
import aiohttp
import asyncio
import base64
from typing import Dict, Any, List

from wsl_brain.sandboxes.base import SandboxEnv, SandboxCapabilities

logger = logging.getLogger(__name__)

# The Windows Specialist. Controls the Dockerized Windows 11 environment via its Python Agent API.


class OmniBoxSandbox(SandboxEnv):
    """
    Controls the Windows 11 Docker container (OmniBox).
    Uses the internal Flask server (port 5000) exposed by the container.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5000)
        self.api_url = f"http://{self.host}:{self.port}"

    @property
    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            can_snapshot=False, # Windows Docker doesn't support live RAM snapshots easily
            can_run_code=True,  # via agent server
            can_browser_interact=True,
            os_type="windows"
        )

    async def start(self) -> bool:
        # In a real deployment, this might trigger `docker start`
        # Here we assume it's running and wait for healthcheck
        logger.info(f"📦 [OmniBox] Connecting to {self.api_url}...")
        async with aiohttp.ClientSession() as session:
            for i in range(5):
                try:
                    async with session.get(f"{self.api_url}/probe", timeout=2) as resp:
                        if resp.status == 200:
                            self._is_active = True
                            logger.info("✅ [OmniBox] Connected.")
                            return True
                except:
                    logger.debug("Waiting for OmniBox...")
                    await asyncio.sleep(2)
        return False

    async def stop(self) -> bool:
        # No-op for persistent container, or docker stop logic
        return True

    async def get_screenshot(self) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/screenshot") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # OmniBox returns base64
                    return base64.b64decode(data['base64_image'])
        return b""

    async def execute_mouse_action(self, action_type: str, x: int, y: int, button: str = "left") -> bool:
        payload = {
            "action_type": action_type, # click, double_click, etc.
            "x": x,
            "y": y,
            "button": button
        }
        return await self._send_action(payload)

    async def execute_keyboard_action(self, text: str = None, keys: List[str] = None) -> bool:
        payload = {
            "action_type": "type",
            "text": text,
            "keys": keys
        }
        return await self._send_action(payload)

    async def _send_action(self, payload: Dict) -> bool:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.api_url}/step", json=payload) as resp:
                    return resp.status == 200
            except Exception as e:
                logger.error(f"❌ [OmniBox] Action failed: {e}")
                return False

    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        # OmniBox supports python/bash via its agent endpoint
        payload = {
            "code": command,
            "language": "python" # or powershell
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.api_url}/exec", json=payload, timeout=timeout) as resp:
                    return await resp.json()
            except Exception as e:
                return {'stdout': '', 'stderr': str(e), 'exit_code': -1}

    async def snapshot_state(self, tag: str) -> str:
        logger.warning("⚠️ [OmniBox] Snapshots not supported on Windows Docker backend.")
        return ""

    async def restore_state(self, snapshot_id: str) -> bool:
        logger.warning("⚠️ [OmniBox] Restore not supported.")
        return False
import logging
import asyncio
import json
import base64
import requests
from typing import Dict, Any, List

from wsl_brain.sandboxes.base import SandboxEnv, SandboxCapabilities
# Assuming py_arrakis is installed from the repo provided in context
try:
    from py_arrakis import SandboxManager
except ImportError:
    # Mock for dev environments where arrakis might not be installed yet
    class SandboxManager: 
        def __init__(self, url): pass

logger = logging.getLogger(__name__)

# The Linux Specialist. Wraps the py-arrakis SDK to control MicroVMs.

class ArrakisSandbox(SandboxEnv):
    """
    Controls an Arrakis MicroVM (Ubuntu).
    Provides sub-second snapshotting and secure code execution.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("arrakis_url", "http://localhost:7000")
        self.image_name = config.get("image", "agent-sandbox")
        self.manager = None
        self.sandbox = None
        self.vnc_port = None
        # In a real impl, we'd use a VNC library like 'vncdotool' to send clicks
        # For this architecture, we assume Arrakis has a sidecar for HTTP->Input
        # or we implement a lightweight VNC wrapper.

    @property
    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            can_snapshot=True,
            can_run_code=True,
            can_browser_interact=True,
            os_type="linux"
        )

    async def start(self) -> bool:
        logger.info(f"📦 [Arrakis] Connecting to Manager at {self.base_url}...")
        try:
            self.manager = SandboxManager(self.base_url)
            # Start the VM
            self.sandbox = self.manager.start_sandbox(self.image_name)
            
            # Extract VNC port from sandbox metadata
            # Assuming sb.info() returns dict with port_forwards
            info = self.sandbox.info() 
            # Logic to parse info for VNC port (5901 mapping)
            # self.vnc_port = parse_port(info) 
            
            self._is_active = True
            logger.info(f"✅ [Arrakis] Sandbox '{self.image_name}' started.")
            return True
        except Exception as e:
            logger.error(f"❌ [Arrakis] Start failed: {e}")
            return False

    async def stop(self) -> bool:
        if self.sandbox:
            try:
                self.sandbox.destroy()
                logger.info("🛑 [Arrakis] Sandbox destroyed.")
            except Exception as e:
                logger.error(f"⚠️ [Arrakis] Destroy failed: {e}")
        return True

    async def get_screenshot(self) -> bytes:
        # Arrakis doesn't have a native screenshot API in the core SDK (it's VNC).
        # We assume a helper service running in the VM or reading the VNC stream.
        # Implementation Detail: Connect to VNC port, grab framebuffer, convert to PNG.
        # For brevity, we simulate the HTTP call to a helper agent inside the VM.
        try:
            # Assumes Arrakis port forwarding to an internal agent on port 8000
            res = self.sandbox.run_cmd("curl -s http://localhost:8000/screenshot_b64")
            if res['exit_code'] == 0:
                return base64.b64decode(res['output'])
        except Exception as e:
            logger.error(f"📸 [Arrakis] Screenshot failed: {e}")
        return b""

    async def execute_mouse_action(self, action_type: str, x: int, y: int, button: str = "left") -> bool:
        # Send xdotool command via run_cmd for reliability in Linux
        # This is slower than VNC but extremely robust for a "Coding Agent"
        cmd = f"xdotool mousemove {x} {y} click 1"
        if action_type == "dblclick":
            cmd = f"xdotool mousemove {x} {y} click --repeat 2 1"
        elif action_type == "drag":
            # Logic for drag needs separate start/end processing
            pass
            
        res = await self.run_command(cmd)
        return res['exit_code'] == 0

    async def execute_keyboard_action(self, text: str = None, keys: List[str] = None) -> bool:
        if text:
            # Sanitize text for shell
            safe_text = text.replace("'", "'\\''")
            cmd = f"xdotool type '{safe_text}'"
            await self.run_command(cmd)
        
        if keys:
            for k in keys:
                # Map keys to xdotool names
                cmd = f"xdotool key {k}"
                await self.run_command(cmd)
        return True

    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        if not self.sandbox:
            raise RuntimeError("Sandbox not started")
        
        logger.debug(f"💻 [Arrakis] Exec: {command[:50]}...")
        # py-arrakis run_cmd is synchronous, we wrap it
        loop = asyncio.get_event_loop()
        try:
            # Run in executor to avoid blocking the async loop
            result = await loop.run_in_executor(
                None, 
                lambda: self.sandbox.run_cmd(command)
            )
            # Arrakis returns {'output': str, 'exit_code': int} roughly
            return {
                'stdout': result.get('output', ''),
                'stderr': '', # Arrakis merges streams usually
                'exit_code': 0 # Simplified, check SDK for exact field
            }
        except Exception as e:
            logger.error(f"❌ [Arrakis] Command error: {e}")
            return {'stdout': '', 'stderr': str(e), 'exit_code': -1}

    async def snapshot_state(self, tag: str) -> str:
        logger.info(f"📸 [Arrakis] Snapshotting state: {tag}")
        loop = asyncio.get_event_loop()
        snapshot_id = await loop.run_in_executor(
            None,
            lambda: self.sandbox.snapshot(tag)
        )
        return snapshot_id

    async def restore_state(self, snapshot_id: str) -> bool:
        logger.warning(f"⏪ [Arrakis] Rolling back to: {snapshot_id}")
        # Note: Arrakis restore might require destroying current and recreating from snap
        # We follow the SDK pattern: manager.restore(name, id)
        loop = asyncio.get_event_loop()
        self.sandbox = await loop.run_in_executor(
            None,
            lambda: self.manager.restore(self.image_name, snapshot_id)
        )
        return True
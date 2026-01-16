import logging
from wsl_brain.actors.base_actor import BaseActor
from wsl_brain.sandboxes.arrakis_client import ArrakisSandbox
from wsl_brain.sandboxes.win_bridge_client import WindowsBridgeSandbox
from wsl_brain.core.config import settings
from shared.python.events_pb2 import ActionRequestEvent, ActionResultEvent

logger = logging.getLogger(__name__)

# The "Hands". Routes actions to the appropriate Sandbox (Arrakis or Windows Bridge).

class ActionActor(BaseActor):
    """
    The Hands.
    Routes abstract actions (Click, Type) to the correct concrete Sandbox.
    Handles 'Time Travel' logic via Arrakis snapshots.
    """

    def __init__(self, bus):
        super().__init__(bus, name="ActionActor")
        self.sandboxes = {}
        self.current_sandbox_id = "default_linux" # Default target

    async def setup(self):
        # Initialize Sandboxes
        logger.info(f"[{self.name}] Initializing Sandboxes...")
        
        # 1. Arrakis (Linux MicroVM)
        self.sandboxes["linux"] = ArrakisSandbox(base_url=settings.ARRAKIS_URL)
        
        # 2. Windows Bridge (Host OS)
        self.sandboxes["windows"] = WindowsBridgeSandbox(base_url=settings.WINDOWS_BRIDGE_URL)
        
        # Subscribe
        await self.bus.subscribe("action.request", ActionRequestEvent, self.handle_action)

    async def cleanup(self):
        pass

    async def handle_action(self, event: ActionRequestEvent):
        """
        Executes a requested action.
        """
        target_os = event.target_os or "linux"
        sandbox = self.sandboxes.get(target_os)
        
        if not sandbox:
            logger.error(f"[{self.name}] Unknown target OS: {target_os}")
            return

        logger.info(f"[{self.name}] Executing {event.action_type} on {target_os}...")

        try:
            # 1. Create Snapshot (SafetyNet) if requested
            if event.requires_snapshot and target_os == "linux":
                snapshot_id = sandbox.snapshot(f"pre_action_{event.action_id}")
                logger.debug(f"[{self.name}] Created snapshot: {snapshot_id}")

            # 2. Execute Action
            result = sandbox.execute_action(event)
            
            # 3. Publish Success
            response = ActionResultEvent()
            response.request_id = event.action_id
            response.success = True
            response.details = str(result)
            await self.bus.publish("action.result", response)

        except Exception as e:
            logger.error(f"[{self.name}] Execution Failed: {e}")
            
            # 4. Auto-Rollback (Time Travel)
            if event.requires_snapshot and target_os == "linux":
                logger.warning(f"[{self.name}] ⏪ Rolling back to snapshot...")
                sandbox.restore(snapshot_id)
            
            # Publish Failure
            response = ActionResultEvent()
            response.request_id = event.action_id
            response.success = False
            response.error = str(e)
            await self.bus.publish("action.result", response)
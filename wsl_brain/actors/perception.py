import logging
import base64
import cv2
import requests
import json
import time
from typing import Dict, Tuple

from wsl_brain.actors.base_actor import BaseActor
from wsl_brain.core.config import settings
from wsl_brain.core.shm_reader import SharedMemoryReader
from wsl_brain.core.resources import gpu_manager
from shared.python.events_pb2 import VisualStateEvent, GroundingRequestEvent, GroundingResultEvent

logger = logging.getLogger(__name__)

# The "Visual Cortex". Connects the Zero-Copy Video Stream to the AI Inference Services.

class PerceptionActor(BaseActor):
    """
    The Eyes of the system.
    1. Reads raw video from Shared Memory (Zero-Copy from Windows).
    2. Sends frames to UI-Ins / OmniParser microservices.
    3. Publishes semantic visual states.
    """

    def __init__(self, bus):
        super().__init__(bus, name="PerceptionActor")
        self.shm_reader = SharedMemoryReader()
        self.last_frame_processed = 0

    async def setup(self):
        # Establish connection to the shared memory block written by Windows
        if not self.shm_reader.connect():
            logger.critical(f"[{self.name}] Failed to connect to Shared Memory Video Buffer!")
        
        # Subscribe to requests
        await self.bus.subscribe("perception.grounding_request", GroundingRequestEvent, self.handle_grounding)
        
        # Start the heartbeat loop (optional: periodic visual scanning)
        self.run_in_background(self._visual_heartbeat())

    async def cleanup(self):
        self.shm_reader.close()

    async def _visual_heartbeat(self):
        """
        Periodically captures the state even if no action is requested, 
        to keep the context cache fresh.
        """
        while self._running:
            # We don't need 30FPS for the agent. 1 FPS is enough for 'awareness'.
            await asyncio.sleep(1.0)
            # Logic to grab frame and maybe run lightweight check could go here
            pass

    async def handle_grounding(self, event: GroundingRequestEvent):
        """
        Handles a request to find specific UI elements (e.g., "Click the Save button").
        Uses UI-Ins for SOTA grounding.
        """
        logger.info(f"[{self.name}] Processing grounding request for: '{event.instruction}'")
        start_time = time.time()

        # 1. Read latest frame from SHM
        # Assumes 4K resolution (adjust in config)
        frame = self.shm_reader.read_frame(width=3840, height=2160)
        
        if frame is None:
            logger.error(f"[{self.name}] Failed to read frame from SHM.")
            await self._publish_error(event.request_id, "Video stream unavailable")
            return

        # 2. Prepare payload for UI-Ins Service
        # We encode to base64 here because the Inference Service is HTTP
        _, buffer = cv2.imencode('.jpg', frame)
        b64_image = base64.b64encode(buffer).decode('utf-8')

        # --- CHANGED HERE ---
        # Acquire Lock before calling UI-Ins
        async with gpu_manager.gpu_lock:
            logger.debug(f"[{self.name}] Acquired GPU Lock")
            try:
                response = requests.post(
                    f"{settings.UI_INS_URL}/ground",
                    json={"base64_image": b64_image, "instruction": event.instruction},
                    timeout=10
                )
                result = response.json()
            finally:
                logger.debug(f"[{self.name}] Released GPU Lock")
        # --------------------

        # # 3. Call UI-Ins Service
        # try:
        #     response = requests.post(
        #         f"{settings.UI_INS_URL}/ground",
        #         json={"base64_image": b64_image, "instruction": event.instruction},
        #         timeout=10
        #     )
        #     response.raise_for_status()
        #     result = response.json() # Expects {x, y, confidence}
        # except Exception as e:
        #     logger.error(f"[{self.name}] UI-Ins Service Failed: {e}")
        #     await self._publish_error(event.request_id, f"Inference failed: {str(e)}")
        #     return

        # latency = time.time() - start_time
        # logger.info(f"[{self.name}] Grounded '{event.instruction}' -> {result['point']} in {latency:.2f}s")

        # 4. Publish Result
        result_event = GroundingResultEvent()
        result_event.request_id = event.request_id
        result_event.x = int(result['point'][0])
        result_event.y = int(result['point'][1])
        result_event.confidence = result.get('confidence', 1.0)
        
        await self.bus.publish("perception.grounding_result", result_event)

    async def _publish_error(self, req_id: str, msg: str):
        # Implementation of error event publishing
        pass
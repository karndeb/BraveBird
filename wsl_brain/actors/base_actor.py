import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Type

from wsl_brain.core.event_bus import EventBus
from shared.python.events_pb2 import BaseEvent  # Assumed generic proto wrapper

logger = logging.getLogger(__name__)

# The Abstract Base Class that standardizes lifecycle management and error handling for all actors.

class BaseActor(ABC):
    """
    Abstract Base Class for all System Actors.
    Enforces the Actor Model pattern: standardized startup, shutdown, and event handling.
    """

    def __init__(self, bus: EventBus, name: str):
        self.bus = bus
        self.name = name
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        """Lifecycle hook: Start the actor."""
        logger.info(f"🎬 [{self.name}] Starting actor...")
        self._running = True
        await self.setup()
        logger.info(f"✅ [{self.name}] Started successfully.")

    async def stop(self):
        """Lifecycle hook: Stop the actor."""
        logger.info(f"🛑 [{self.name}] Stopping actor...")
        self._running = False
        
        # Cancel internal tasks
        for task in self._tasks:
            task.cancel()
        
        await self.cleanup()
        logger.info(f"👋 [{self.name}] Stopped.")

    @abstractmethod
    async def setup(self):
        """Initialize resources (models, connections) here."""
        pass

    @abstractmethod
    async def cleanup(self):
        """Release resources here."""
        pass

    def run_in_background(self, coroutine):
        """Helper to fire-and-forget async tasks within the actor scope."""
        task = asyncio.create_task(coroutine)
        self._tasks.append(task)
        task.add_done_callback(self._tasks.remove)
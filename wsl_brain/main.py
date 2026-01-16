import asyncio
import logging
import signal
import sys
from typing import List

from wsl_brain.core.config import settings
from wsl_brain.core.event_bus import EventBus
from wsl_brain.actors.base_actor import BaseActor

# Import Actors
from wsl_brain.actors.perception import PerceptionActor
from wsl_brain.actors.cognition import CognitionActor
from wsl_brain.actors.action import ActionActor
from wsl_brain.actors.audio import AudioActor

# Configure Logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("brain.log")
    ]
)

logger = logging.getLogger("BravebirdBrain")

# This is the Orchestrator. 
# It bootstraps the Actor System, manages lifecycles, handles graceful shutdowns, and keeps the Brain alive. It implements the Composition Root pattern.

class BrainOrchestrator:
    """
    The Main Process. 
    Initializes the Event Bus and manages the lifecycle of all Actors.
    """

    def __init__(self):
        self.bus = EventBus()
        self.actors: List[BaseActor] = []
        self._stopping = False

    async def bootstrap(self):
        """Initialize all components."""
        logger.info("🧠 Bootstrapping Bravebird Brain...")
        
        # 1. Start Nervous System
        await self.bus.connect()

        # 2. Instantiate Actors (Dependency Injection via Bus)
        # Perception: Eyes (OmniParser/UI-Ins)
        self.actors.append(PerceptionActor(self.bus))
        
        # Audio: Ears (Whisper)
        self.actors.append(AudioActor(self.bus))
        
        # Cognition: Frontal Cortex (Gemini Flash)
        self.actors.append(CognitionActor(self.bus))
        
        # Action: Hands (Arrakis/Bridge)
        self.actors.append(ActionActor(self.bus))

        logger.info(f"🧩 Initialized {len(self.actors)} Actors.")

    async def start(self):
        """Start all actors concurrently."""
        logger.info("🚀 Starting all Actors...")
        
        # Run startup routines in parallel
        start_tasks = [actor.start() for actor in self.actors]
        await asyncio.gather(*start_tasks)
        
        logger.info("✨ System Online. Waiting for inputs...")

    async def shutdown(self):
        """Graceful shutdown sequence."""
        if self._stopping:
            return
        self._stopping = True
        
        logger.info("🛑 Shutting down system...")
        
        # Stop actors in reverse order (Good practice)
        for actor in reversed(self.actors):
            try:
                await actor.stop()
            except Exception as e:
                logger.error(f"Error stopping {actor.name}: {e}")

        # Close Bus
        if self.bus:
            await self.bus.disconnect()
            
        logger.info("💀 System Offline.")

def handle_signals(orchestrator: BrainOrchestrator):
    """Register signal handlers for graceful exit (Ctrl+C)."""
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("⚠️ Signal received. Initiating shutdown...")
        asyncio.create_task(orchestrator.shutdown())
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

async def main():
    orchestrator = BrainOrchestrator()
    
    try:
        handle_signals(orchestrator)
        await orchestrator.bootstrap()
        await orchestrator.start()
        
        # Keep the main loop alive forever until a signal is received
        # This allows actors to run their background tasks
        while not orchestrator._stopping:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical(f"🔥 Critical Failure: {e}", exc_info=True)
    finally:
        await orchestrator.shutdown()

if __name__ == "__main__":
    # Windows does not support 'uvloop', but we are in WSL (Linux), so we use it for speed.
    try:
        import uvloop
        uvloop.install()
        logger.info("🚀 Using uvloop for high-performance asyncio.")
    except ImportError:
        logger.warning("⚠️ uvloop not found. Using standard asyncio loop.")
        
    asyncio.run(main())
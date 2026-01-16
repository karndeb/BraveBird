import asyncio
import logging
import time
import sys
import os

# Ensure we can import from local modules
sys.path.append(os.getcwd())

from wsl_brain.core.event_bus import EventBus
from shared.python.events_pb2 import UserTranscriptEvent

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TRIGGER] %(message)s"
)
logger = logging.getLogger("DebugTrigger")

async def trigger_command(text_command: str):
    """
    Injects a fake user voice command into the Redis Bus.
    """
    logger.info("🔌 Connecting to Event Bus...")
    
    # 1. Connect
    # Note: We use "debug_tool" as service name
    bus = EventBus()
    await bus.connect()

    # 2. Create Event
    event = UserTranscriptEvent()
    event.text = text_command
    event.timestamp = int(time.time() * 1000)

    # 3. Publish
    channel = "cognition.user_voice"
    logger.info(f"📤 Injecting command: '{text_command}' into channel '{channel}'")
    
    await bus.publish(channel, event)
    
    # Allow time for message to flush
    await asyncio.sleep(0.5)
    
    # 4. Disconnect
    await bus.disconnect()
    logger.info("✅ Injection complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        # Default test command
        command = "Open the calculator and type 55 plus 55"
    
    asyncio.run(trigger_command(command))
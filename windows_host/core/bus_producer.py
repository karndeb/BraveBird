import logging
import redis
import time
from typing import Optional
from google.protobuf.message import Message

# Import generated Protobuf classes
# Note: Ensure the 'shared' directory is in PYTHONPATH
from shared.python.events_pb2 import BusEvent

# Import Windows Config
from windows_host.config import WindowsConfig

logger = logging.getLogger("BusProducer")

# The "Nervous System Transmitter".
# This class is responsible for high-performance, non-blocking event publishing. It uses a Redis Connection Pool to ensure low latency when pushing thousands of mouse events or audio chunks per minute.

class BusProducer:
    """
    High-performance Event Publisher for the Windows Host.
    Publishes Protobuf messages to the Redis instance running in WSL.
    
    Design Pattern: Singleton-ish (managed by Main) / Producer.
    """

    def __init__(self, config: WindowsConfig):
        self.config = config
        self._redis_client: Optional[redis.Redis] = None
        self._is_connected = False

    def connect(self):
        """Establishes connection to the WSL Redis server."""
        try:
            logger.info(f"🔌 Connecting to Redis Bus at {self.config.REDIS_HOST}:{self.config.REDIS_PORT}...")
            
            # Use a connection pool for thread safety and performance
            pool = redis.ConnectionPool(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=False # We are sending binary Protobufs
            )
            self._redis_client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self._redis_client.ping()
            self._is_connected = True
            logger.info("✅ Connected to Event Bus.")
            
        except redis.ConnectionError as e:
            logger.critical(f"❌ Failed to connect to Redis: {e}")
            self._is_connected = False
            raise e

    def publish(self, channel: str, message: Message, event_id: str = None):
        """
        Publishes a Protobuf message to a specific channel.
        
        Args:
            channel: The topic (e.g., 'input.mouse', 'video.frames').
            message: The specific Protobuf object (e.g., MouseEvent).
            event_id: Optional UUID for tracing.
        """
        if not self._is_connected or not self._redis_client:
            logger.warning("⚠️ Attempted to publish while disconnected.")
            return

        try:
            # Wrap in the generic BusEvent envelope if needed, 
            # or send raw bytes if the subscriber expects specific types.
            # Here we assume subscribers listen for specific proto types on specific channels.
            
            payload = message.SerializeToString()
            
            # --- CHANGED HERE ---
            # Old: self._redis_client.publish(channel, payload)
            # New: Use Redis Stream (XADD). maxlen caps the buffer to prevent RAM overflow.
            self._redis_client.xadd(channel, {"data": payload}, maxlen=2000)
            # --------------------
            
            # Debug log (verbose only for low-frequency events)
            if "video" not in channel and "audio" not in channel:
                logger.debug(f"📤 Published to [{channel}]: {len(payload)} bytes")
                
        except Exception as e:
            logger.error(f"❌ Publish failed on {channel}: {e}")

    def close(self):
        """Closes the Redis connection."""
        if self._redis_client:
            self._redis_client.close()
            self._is_connected = False
            logger.info("🔒 Bus Producer closed.")
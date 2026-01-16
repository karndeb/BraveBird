import logging
import asyncio
import redis.asyncio as redis
from typing import Callable, Dict, Any, Type, TypeVar
from google.protobuf.message import Message

from wsl_brain.core.config import settings

# Type variable for Protobuf messages
T = TypeVar('T', bound=Message)

logger = logging.getLogger(__name__)

# A robust wrapper around Redis Pub/Sub that handles Protobuf serialization transparently. 
# It implements the Observer Pattern.

class EventBus:
    """
    Asynchronous Event Bus using Redis Pub/Sub.
    Handles automatic serialization/deserialization of Protobuf messages.
    """

    def __init__(self):
        self._redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        self._redis: redis.Redis = None
        self._pubsub = None
        self._handlers: Dict[str, list[Callable[[Any], None]]] = {}
        self._running = False

    async def connect(self):
        """Initializes the Redis connection."""
        try:
            self._redis = redis.from_url(self._redis_url)
            self._pubsub = self._redis.pubsub()
            logger.info(f"🔌 Connected to Event Bus at {self._redis_url}")
            self._running = True
            # Start the listener loop in the background
            asyncio.create_task(self._listener_loop())
        except Exception as e:
            logger.critical(f"❌ Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Closes Redis connection."""
        self._running = False
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("🔌 Disconnected from Event Bus")

    async def publish(self, channel: str, message: Message):
        """
        Publishes a Protobuf message to a channel.
        
        Args:
            channel: The topic name.
            message: A valid Protobuf object.
        """
        if not self._redis:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        
        try:
            # Serialize Protobuf to bytes
            payload = message.SerializeToString()
            await self._redis.publish(channel, payload)
            # Debug log for high-level events (filtering out high-frequency streams like video)
            if "video" not in channel:
                logger.debug(f"📤 Published to [{channel}]: {type(message).__name__}")
        except Exception as e:
            logger.error(f"❌ Failed to publish to {channel}: {e}")

    async def subscribe(self, channel: str, message_type: Type[T], callback: Callable[[T], Any]):
        """
        Subscribes to a channel with a typed callback.

        Args:
            channel: The topic name.
            message_type: The Protobuf class to deserialize into (e.g. VisualFrame).
            callback: Async function that accepts the deserialized message.
        """
        if channel not in self._handlers:
            self._handlers[channel] = []
            await self._pubsub.subscribe(channel)
            logger.info(f"👂 Subscribed to channel: [{channel}]")

        # Store the wrapper to handle deserialization logic
        self._handlers[channel].append({
            "type": message_type,
            "func": callback
        })

    async def _listener_loop(self):
        logger.info("🔄 Stream Polling Loop started")
        
        while self._running:
            try:
                # --- CHANGED HERE ---
                # Poll all registered streams using XREADGROUP
                streams = {k: ">" for k in self._handlers.keys()} # ">" means new messages
                if not streams:
                    await asyncio.sleep(0.1)
                    continue

                # Block for 100ms waiting for data
                events = await self.redis.xreadgroup("brain_workers", "worker_1", streams, count=10, block=100)
                
                for stream_name, messages in events:
                    stream_str = stream_name.decode("utf-8")
                    handler = self._handlers.get(stream_str)
                    
                    for msg_id, msg_data in messages:
                        # Process
                        await self._process_message(handler, msg_data[b'data'], stream_str)
                        # ACK the message (Mark processed)
                        await self.redis.xack(stream_str, "brain_workers", msg_id)
                # --------------------
                
            except Exception as e:
                logger.error(f"❌ Stream Loop Error: {e}")
                await asyncio.sleep(1)

    async def _process_message(self, handler_config, raw_data: bytes, channel: str):
        """Deserializes data and invokes the callback safely."""
        try:
            msg_type = handler_config["type"]
            callback = handler_config["func"]
            
            # Deserialize
            proto_instance = msg_type()
            proto_instance.ParseFromString(raw_data)
            
            # Invoke callback
            if asyncio.iscoroutinefunction(callback):
                await callback(proto_instance)
            else:
                callback(proto_instance)
        except Exception as e:
            logger.error(f"❌ Error processing message on [{channel}]: {e}")
import logging
import io
import numpy as np
from faster_whisper import WhisperModel

from wsl_brain.actors.base_actor import BaseActor
from wsl_brain.core.config import settings
from wsl_brain.core.resources import gpu_manager
from shared.python.events_pb2 import AudioChunkEvent, UserTranscriptEvent

logger = logging.getLogger(__name__)

# The "Ears". Uses faster-whisper locally for low-latency command recognition.

class AudioActor(BaseActor):
    """
    The Ears. 
    Consumes raw audio chunks from Windows VAD.
    Runs local STT (Speech-to-Text) to drive the agent.
    """

    def __init__(self, bus):
        super().__init__(bus, name="AudioActor")
        self.model = None

    async def setup(self):
        logger.info(f"[{self.name}] Loading Whisper model ({settings.WHISPER_MODEL_SIZE})...")
        # Load model on GPU if available
        device = "cuda" if settings.USE_CUDA else "cpu"
        self.model = WhisperModel(settings.WHISPER_MODEL_SIZE, device=device, compute_type="float16")
        
        await self.bus.subscribe("input.audio_chunk", AudioChunkEvent, self.handle_audio)
        logger.info(f"[{self.name}] Listening for voice commands.")

    async def cleanup(self):
        # Cleanup model resources if needed
        pass

    async def handle_audio(self, event: AudioChunkEvent):
        """
        Process a chunk of audio detected by VAD on Windows.
        """
        # 1. Decode raw bytes to numpy array (float32)
        audio_data = np.frombuffer(event.data, dtype=np.float32)
        
        # 2. Transcribe
        # beam_size=1 for speed, we need low latency commands
        async with gpu_manager.gpu_lock:
            segments, info = self.model.transcribe(audio_data, beam_size=1, language="en")
        
        full_text = " ".join([segment.text for segment in segments]).strip()

        if full_text:
            logger.info(f"[{self.name}] Heard: '{full_text}'")
            
            # 3. Publish Transcript
            transcript_event = UserTranscriptEvent()
            transcript_event.text = full_text
            transcript_event.timestamp = event.timestamp
            
            await self.bus.publish("cognition.user_voice", transcript_event)
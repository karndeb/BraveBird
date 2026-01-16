import logging
import webrtcvad
import collections
from typing import Optional, List

from windows_host.config import WindowsConfig

logger = logging.getLogger("VADFilter")

# Logic to detect speech vs. background noise. Prevents flooding the Event Bus with silence.

class VADFilter:
    """
    Voice Activity Detection Filter.
    Uses WebRTC's VAD algorithm to determine if an audio frame contains speech.
    Aggregates frames into meaningful chunks to send to the Whisper Agent.
    """

    def __init__(self, config: WindowsConfig):
        # Mode 3 is the most aggressive filtering (least false positives)
        self.vad = webrtcvad.Vad(3)
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.frame_duration_ms = config.AUDIO_FRAME_DURATION_MS
        
        # Calculate expected bytes per frame for validation
        # (Sample Rate * Bit Depth * Duration) / 8
        # e.g., (16000 * 16 * 0.02) / 8 = 640 bytes
        self.bytes_per_frame = int(self.sample_rate * 2 * (self.frame_duration_ms / 1000))
        
        # Ring buffer to smooth out detection (avoid chopping words)
        self._ring_buffer = collections.deque(maxlen=10)
        self._triggered = False

    def is_speech(self, frame: bytes) -> bool:
        """
        Returns True if the frame contains speech.
        """
        if len(frame) != self.bytes_per_frame:
            logger.warning(f"⚠️ Invalid frame size: {len(frame)} bytes. Expected {self.bytes_per_frame}.")
            return False

        try:
            is_speech = self.vad.is_speech(frame, self.sample_rate)
            
            # Simple smoothing logic
            self._ring_buffer.append(is_speech)
            
            # Trigger if > 60% of buffer is speech
            active_ratio = sum(self._ring_buffer) / len(self._ring_buffer)
            
            if not self._triggered and active_ratio > 0.6:
                self._triggered = True
                # logger.debug("🗣️ Voice activity started")
                return True
            
            if self._triggered and active_ratio < 0.2:
                self._triggered = False
                # logger.debug("🤫 Voice activity ended")
                return False
                
            return self._triggered

        except Exception as e:
            logger.error(f"VAD Error: {e}")
            return False
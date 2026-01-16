import pyaudio
import logging
import threading
import time

from windows_host.config import WindowsConfig
from windows_host.core.bus_producer import BusProducer
from windows_host.audio.vad_filter import VADFilter
from shared.python.events_pb2 import AudioChunk

logger = logging.getLogger("MicrophoneStream")

# Wraps PortAudio via pyaudio. Runs in a background thread to prevent blocking.

class MicrophoneStream:
    """
    Captures raw audio from the default input device.
    Filters through VAD and publishes 'AudioChunk' events to Redis.
    """

    def __init__(self, config: WindowsConfig, bus: BusProducer):
        self.config = config
        self.bus = bus
        self.vad = VADFilter(config)
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self._running = False
        self._thread = None

    def start(self):
        """Starts the audio capture loop."""
        if self._running: return

        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.config.audio_chunk_size
            )
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info("🎤 Microphone listening...")
        except Exception as e:
            logger.error(f"❌ Failed to open microphone: {e}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()
        logger.info("🎤 Microphone stopped.")

    def _capture_loop(self):
        """Continuous capture loop."""
        while self._running:
            try:
                # Read raw bytes
                # exception_on_overflow=False prevents crashes on heavy load
                data = self.stream.read(self.config.audio_chunk_size, exception_on_overflow=False)
                
                # Check VAD
                if self.vad.is_speech(data):
                    # Construct Event
                    event = AudioChunk()
                    event.timestamp = int(time.time() * 1000)
                    event.data = data
                    event.sample_rate = self.config.AUDIO_SAMPLE_RATE
                    event.is_speech = True

                    # Publish to 'input.audio' channel
                    self.bus.publish("input.audio_chunk", event)

            except OSError as e:
                # Common if device is lost or buffer overflows
                logger.warning(f"Audio buffer warning: {e}")
            except Exception as e:
                logger.error(f"Audio loop crash: {e}")
                self._running = False
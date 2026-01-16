import os
from pydantic_settings import BaseSettings
from typing import Tuple

class WindowsConfig(BaseSettings):
    """
    Configuration for the Windows Host Agent.
    """
    
    # --- Redis (WSL Host) ---
    # In WSL 2, the Linux host is usually accessible via 'localhost' 
    # if mapped correctly, or a specific IP. 
    # For default setups, 'localhost' often works if ports are forwarded.
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # --- Shared Memory ---
    # Path on the Windows Filesystem
    # WSL must have this mounted at /mnt/c/temp/bravebird_video.shm
    SHM_FILE_PATH: str = r"C:\temp\bravebird_video.shm"
    
    # --- Screen Capture ---
    CAPTURE_FPS: int = 5 # Low FPS to save tokens, we rely on event triggers
    SCREEN_WIDTH: int = 1920
    SCREEN_HEIGHT: int = 1080
    
    # --- Audio ---
    # WebRTC VAD requires 16000Hz and specific frame durations (10, 20, or 30ms)
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_FRAME_DURATION_MS: int = 20 # 20ms
    
    @property
    def audio_chunk_size(self) -> int:
        """Calculates buffer size in samples."""
        return int(self.AUDIO_SAMPLE_RATE * (self.AUDIO_FRAME_DURATION_MS / 1000))

    # --- Bridge Server ---
    HOST_IP: str = "0.0.0.0"
    BRIDGE_PORT: int = 5050 # Port for WSL to send commands back to Windows

    class Config:
        env_prefix = "BB_WIN_"
        env_file = ".env"

# Instantiate
config = WindowsConfig()
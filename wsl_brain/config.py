import os
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

class SystemConfig(BaseSettings):
    """
    Global Configuration for the WSL Brain.
    
    Loads values from:
    1. Environment Variables (prefixed with BB_)
    2. .env file in the root directory
    3. Default values defined here
    """

    # --- General ---
    ENV: EnvironmentType = EnvironmentType.DEVELOPMENT
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.resolve()
    LOG_LEVEL: str = "INFO"
    
    # --- Redis (The Nervous System) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # --- Shared Memory (Zero-Copy Video Bridge) ---
    # Windows path: C:\temp\bravebird_video.shm
    # WSL mount: /mnt/c/temp/bravebird_video.shm
    SHM_FILE_PATH: str = "/mnt/c/temp/bravebird_video.shm"
    # Resolution must match what Windows Host is capturing
    SCREEN_WIDTH: int = 1920 
    SCREEN_HEIGHT: int = 1080
    
    # --- AI Models (The Brains) ---
    # Gemini (Cognition & Planning)
    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    
    # Whisper (Audio)
    WHISPER_MODEL_SIZE: str = "distil-medium.en"
    USE_CUDA: bool = True

    # --- Microservices (The Workers) ---
    # These run as separate processes/containers defined in docker-compose
    UI_INS_URL: str = "http://localhost:8001"
    OMNIPARSER_URL: str = "http://localhost:8002"
    
    # --- Execution Environments ---
    # Arrakis (Linux Sandbox)
    ARRAKIS_URL: str = "http://localhost:7000"
    ARRAKIS_DEFAULT_IMAGE: str = "agent-sandbox"
    
    # OmniBox (Windows Docker Sandbox)
    OMNIBOX_HOST: str = "localhost"
    OMNIBOX_PORT: int = 5000
    
    # Windows Host Bridge
    # Accessing the host from WSL usually requires specific IP or host.docker.internal
    WINDOWS_BRIDGE_URL: str = "http://host.docker.internal:5050"

    # --- Paths ---
    DATA_DIR: Path = PROJECT_ROOT / "data"
    WEIGHTS_DIR: Path = DATA_DIR / "weights"
    TRACES_DIR: Path = DATA_DIR / "raw_traces"
    WORKFLOWS_DIR: Path = DATA_DIR / "workflows"

    class Config:
        env_prefix = "BB_"
        env_file = ".env"
        case_sensitive = True

# Singleton Instance
settings = SystemConfig()
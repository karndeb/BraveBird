import os
from pydantic_settings import BaseSettings
from enum import Enum

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class SystemConfig(BaseSettings):
    """
    Global configuration for the WSL Brain.
    Reads from environment variables (e.g. BB_REDIS_HOST) or .env file.
    """
    
    # Environment
    ENV: EnvironmentType = EnvironmentType.DEVELOPMENT
    LOG_LEVEL: str = "INFO"
    
    # Redis (Event Bus)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Shared Memory / IPC
    # Path accessible by both Windows (C:\temp) and WSL (/mnt/c/temp)
    SHM_FILE_PATH: str = "/mnt/c/temp/bravebird_video.shm"
    SHM_SIZE_MB: int = 64  # Buffer size for 4K frames
    
    # AI Model Endpoints
    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    
    # Service Endpoints
    UI_INS_URL: str = "http://localhost:8001"
    OMNIPARSER_URL: str = "http://localhost:8002"
    ARRAKIS_URL: str = "http://localhost:7000"
    WINDOWS_BRIDGE_URL: str = "http://host.docker.internal:5000"

    class Config:
        env_prefix = "BB_"
        env_file = ".env"

# Singleton instance
settings = SystemConfig()
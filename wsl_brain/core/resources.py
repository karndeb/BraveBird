import asyncio

class ResourceManager:
    def __init__(self):
        # Global lock to ensure only one heavy model runs on the GPU at a time
        self.gpu_lock = asyncio.Lock()

# Singleton instance
gpu_manager = ResourceManager()
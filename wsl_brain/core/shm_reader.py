import mmap
import os
import logging
import numpy as np
import cv2
from typing import Optional

from wsl_brain.core.config import settings

logger = logging.getLogger(__name__)

# This implements the Zero-Copy mechanism. 
# It uses memory-mapped files to read video frames written by the Windows Host, avoiding network serialization overhead.

class SharedMemoryReader:
    """
    Reads raw video frames from a memory-mapped file shared with the Windows Host.
    
    Design Pattern: Zero-Copy Access
    The Windows host writes pixels to a file on /mnt/c/. We mmap that file here.
    """

    def __init__(self):
        self.file_path = settings.SHM_FILE_PATH
        self.file_handle = None
        self.mmap_obj = None
        self._connected = False

    def connect(self):
        """Opens the memory mapped file."""
        if not os.path.exists(self.file_path):
            logger.warning(f"⚠️ SHM file not found at {self.file_path}. Waiting for Windows Host...")
            return False

        try:
            self.file_handle = open(self.file_path, "r+b")
            self.mmap_obj = mmap.mmap(
                self.file_handle.fileno(), 
                length=0, 
                access=mmap.ACCESS_READ
            )
            self._connected = True
            logger.info(f"🔗 Connected to Shared Memory at {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to SHM: {e}")
            return False

    def read_frame(self, width: int, height: int, offset: int = 0) -> Optional[np.ndarray]:
        """
        Reads a frame from the shared buffer.

        Args:
            width: Image width
            height: Image height
            offset: Byte offset in the SHM where the frame data begins.
        
        Returns:
            numpy.ndarray (BGR format) or None if read failed.
        """
        if not self._connected:
            if not self.connect():
                return None

        # Calculate expected size (assuming BGRA or RGB from Windows)
        # Usually Windows DXGI returns BGRA (4 bytes per pixel)
        expected_bytes = width * height * 4 

        try:
            self.mmap_obj.seek(offset)
            raw_data = self.mmap_obj.read(expected_bytes)
            
            if len(raw_data) != expected_bytes:
                logger.warning("⚠️ Incomplete frame data read from SHM")
                return None

            # Convert bytes to numpy array (Zero-Copy view if possible)
            # Note: We copy here to avoid blocking the mmap, but np.frombuffer is fast
            arr = np.frombuffer(raw_data, dtype=np.uint8)
            
            # Reshape to Image (H, W, Channels)
            image = arr.reshape((height, width, 4))
            
            # Drop Alpha channel if not needed (convert BGRA -> BGR)
            image = image[..., :3] 
            
            return image

        except ValueError as e:
            logger.error(f"❌ Error reading frame from SHM: {e}")
            return None

    def close(self):
        if self.mmap_obj:
            self.mmap_obj.close()
        if self.file_handle:
            self.file_handle.close()
        self._connected = False
        logger.info("🔒 Closed Shared Memory connection")
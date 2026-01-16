import mmap
import os
import time
import logging
import threading
import numpy as np
import mss
import struct
from typing import Tuple

from windows_host.config import WindowsConfig
from shared.python.events_pb2 import VisualFrame

logger = logging.getLogger("ScreenCapturer")

# The "Eyes".
# Optimization Technique: Memory Mapped Files (mmap).
# Instead of sending video over TCP/HTTP (which adds latency and CPU overhead), we write raw pixel data directly to a file on the NTFS drive. 
# WSL 2 mounts the C: drive at /mnt/c/, allowing the Linux Brain to read this memory almost instantly (Zero-Copy-ish).

class ScreenCapturer:
    """
    High-Performance Screen Capture writing to a Shared Memory File.
    
    Protocol:
    [8 bytes: timestamp (double)]
    [4 bytes: width (int)]
    [4 bytes: height (int)]
    [N bytes: Raw BGRA Pixel Data]
    """

    def __init__(self, config: WindowsConfig, bus_producer, session_manager=None):
        self.config = config
        self.bus = bus_producer
        self.session = session_manager 
        self._running = False
        self._thread = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config.SHM_FILE_PATH), exist_ok=True)
        
        # Calculate buffer size for 4K BGRA (Worst case)
        # 3840 * 2160 * 4 bytes ~= 33 MB
        self.buffer_size = 3840 * 2160 * 4 + 16 # +16 for header
        
        # Initialize mmap file
        self._init_shm()

    def _init_shm(self):
        """Creates/Resets the file backing the shared memory."""
        try:
            with open(self.config.SHM_FILE_PATH, "wb") as f:
                f.write(b'\0' * self.buffer_size)
            logger.info(f"💾 Initialized Shared Memory file at {self.config.SHM_FILE_PATH} ({self.buffer_size / 1024 / 1024:.2f} MB)")
        except Exception as e:
            logger.critical(f"❌ Failed to init SHM: {e}")
            raise

    def start(self):
        """Starts the capture loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("🎥 Screen Capture thread started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        logger.info("🎥 Screen Capture stopped.")

    def _capture_loop(self):
        """
        Continuously grabs frames and writes to mmap.
        """
        # Open mmap in write mode
        try:
            with open(self.config.SHM_FILE_PATH, "r+b") as f:
                with mmap.mmap(f.fileno(), self.buffer_size, access=mmap.ACCESS_WRITE) as mm:
                    with mss.mss() as sct:
                        # Capture monitor 1
                        monitor = sct.monitors[1] 
                        
                        while self._running:
                            start_time = time.time()
                            
                            # 1. Grab Frame
                            screenshot = sct.grab(monitor)
                            
                            # 2. Get Raw Bytes (BGRA)
                            raw_bytes = screenshot.raw
                            width = screenshot.width
                            height = screenshot.height
                            
                            # 3. Write Header (Timestamp, W, H)
                            # 'd' = double, 'i' = int
                            header = struct.pack('dii', start_time, width, height)
                            
                            # 4. Write to Shared Memory
                            # mm.seek(0)
                            # mm.write(header)
                            # mm.write(raw_bytes)
                            # mm.flush() # Ensure sync to disk/WSL
                            
                            # Write to Disk
                            if self.session:
                                self.session.write_video_frame(raw_bytes)

                            # 5. Notify Bus (Optional - only if we want event-driven video)
                            # For bandwidth saving, we might NOT send a bus event for every frame,
                            # letting the consumer poll the SHM file instead. 
                            # However, sending a lightweight pointer event is good practice.
                            
                            frame_event = VisualFrame()
                            frame_event.timestamp = int(start_time * 1000)
                            frame_event.width = width
                            frame_event.height = height
                            frame_event.shm_handle = self.config.SHM_FILE_PATH
                            frame_event.encoding = "raw_bgra"
                            
                            self.bus.publish("video.frame_ready", frame_event)

                            # Cap FPS
                            elapsed = time.time() - start_time
                            sleep_time = max(0, (1.0 / self.config.CAPTURE_FPS) - elapsed)
                            time.sleep(sleep_time)

        except Exception as e:
            logger.critical(f"❌ Capture loop crashed: {e}")
            self._running = False
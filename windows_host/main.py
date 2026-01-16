import logging
import time
import sys
import threading
import signal

from windows_host.config import config
from windows_host.core.bus_producer import BusProducer
from windows_host.core.bridge_server import BridgeServer
from windows_host.capture.fast_screen import ScreenCapturer
from windows_host.capture.inputs import InputListener
from windows_host.audio.mic_stream import MicrophoneStream
from windows_host.recorder.session import SessionManager
# Setup Console Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WIN_HOST] [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("Main")

class WindowsHostApp:
    def __init__(self):
        self.running = False
        
        # 1. Initialize Bus (Outbound)
        self.bus = BusProducer(config)
        
        # 2. Initialize Bridge (Inbound)
        self.bridge = BridgeServer(config)
        
        # 3. Initialize Sensors
        self.screen = ScreenCapturer(config, self.bus)
        self.inputs = InputListener(self.bus)
        self.audio = MicrophoneStream(config, self.bus)

        # --- CHANGED HERE ---
        # Create a session ID based on timestamp
        session_id = f"trace_{int(time.time())}"
        self.session = SessionManager(session_id)
        self.session.start_recording()
        
        # Pass session to sensors
        self.screen = ScreenCapturer(config, self.bus, self.session)
        self.inputs = InputListener(self.bus, self.session)
        # --------------------

    def start(self):
        logger.info("🚀 Starting Bravebird Windows Host...")
        
        try:
            # Connect to Redis (WSL)
            self.bus.connect()
            
            # Start Action Receiver
            self.bridge.start()
            
            # Start Sensors
            self.screen.start()
            self.inputs.start()
            self.audio.start()
            
            self.running = True
            logger.info("✨ Windows Host Online. Press Ctrl+C to stop.")
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⚠️ Interrupted by user.")
            self.stop()
        except Exception as e:
            logger.critical(f"🔥 Startup failed: {e}", exc_info=True)
            self.stop()

    def stop(self):
        if not self.running: return
        self.running = False
        
        logger.info("🛑 Shutting down services...")
        
        # Shutdown in reverse dependency order
        self.audio.stop()
        self.inputs.stop()
        self.screen.stop()
        self.bridge.stop()
        self.bus.close()
        self.session.close() # Ensure video saves correctly
        logger.info("💀 Windows Host Offline.")
        sys.exit(0)

if __name__ == "__main__":
    app = WindowsHostApp()
    app.start()
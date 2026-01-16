import logging
import threading
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

from windows_host.core.controller import WindowsController
from windows_host.config import WindowsConfig

logger = logging.getLogger("BridgeServer")

# The "Command Receiver".
# This is a lightweight Flask server. 
# Why Flask and not FastAPI here? Because on Windows (native), installing complex async dependencies can sometimes conflict with pywinauto or COM threading models. 
# Flask is synchronous, stable, and perfectly sufficient for receiving sparse commands from the Agent.

class BridgeServer:
    """
    HTTP Server listening for commands from the WSL Brain.
    Runs in a dedicated thread to avoid blocking the Capture Loop.
    
    Endpoints:
    - GET /status: Health check
    - POST /action: Execute mouse/keyboard action
    """

    def __init__(self, config: WindowsConfig):
        self.config = config
        self.app = Flask(__name__)
        self.controller = WindowsController()
        self.server = None
        self.thread = None
        
        # Register Routes
        self.app.add_url_rule('/status', 'status', self.status_handler, methods=['GET'])
        self.app.add_url_rule('/action', 'action', self.action_handler, methods=['POST'])

    def status_handler(self):
        """Health check endpoint."""
        return jsonify({
            "status": "online",
            "resolution": self.controller.get_screen_size()
        })

    def action_handler(self):
        """
        Receives an Action Payload from WSL Agent.
        Schema: {
            "type": "click"|"type"|"scroll",
            "x": int, "y": int, "button": str,
            "text": str, "keys": list
        }
        """
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        action_type = data.get("type")
        
        try:
            if action_type == "click":
                self.controller.execute_click(
                    x=int(data.get("x", 0)),
                    y=int(data.get("y", 0)),
                    button=data.get("button", "left"),
                    double=data.get("double", False)
                )
            
            elif action_type == "type":
                self.controller.execute_type(
                    text=data.get("text"),
                    keys=data.get("keys")
                )
            
            elif action_type == "scroll":
                self.controller.execute_scroll(
                    amount=int(data.get("amount", 0))
                )
            
            else:
                logger.warning(f"⚠️ Unknown action type: {action_type}")
                return jsonify({"error": "Unknown action type"}), 400

            return jsonify({"status": "success"})
            
        except Exception as e:
            logger.error(f"❌ Error executing action: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    def start(self):
        """Starts the Flask server in a background thread."""
        logger.info(f"🚀 Starting Bridge Server on port {self.config.BRIDGE_PORT}...")
        self.server = make_server(self.config.HOST_IP, self.config.BRIDGE_PORT, self.app)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True # Kill thread when main process exits
        self.thread.start()

    def stop(self):
        """Stops the server."""
        if self.server:
            logger.info("🛑 Stopping Bridge Server...")
            self.server.shutdown()
            self.thread.join()
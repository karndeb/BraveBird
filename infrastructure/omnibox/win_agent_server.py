"""
Lightweight HTTP Server for Windows Agent Control.
Runs inside the OmniBox VM.
"""
import logging
import pyautogui
from flask import Flask, request, jsonify
from PIL import ImageGrab
import io
import base64

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# The "Nervous System" of the Windows VM. This runs inside Windows 11.

# Configure PyAutoGUI
pyautogui.FAILSAFE = False

@app.route('/probe', methods=['GET'])
def probe():
    """Health check."""
    return jsonify({"status": "ready", "os": "windows_11"})

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    """Captures the current screen state."""
    try:
        screenshot = ImageGrab.grab()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        b64_str = base64.b64encode(buffer.getvalue()).decode()
        return jsonify({"base64_image": b64_str})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/step', methods=['POST'])
def execute_step():
    """Executes a mouse/keyboard action."""
    data = request.json
    action_type = data.get("action_type")
    
    try:
        if action_type == "click":
            pyautogui.click(x=data['x'], y=data['y'], button=data.get('button', 'left'))
        
        elif action_type == "double_click":
            pyautogui.doubleClick(x=data['x'], y=data['y'])
            
        elif action_type == "type":
            # Focus is assumed to be set by a previous click
            if data.get('text'):
                pyautogui.write(data['text'], interval=0.01)
            if data.get('keys'):
                # Handle hotkeys like ['ctrl', 'c']
                pyautogui.hotkey(*data['keys'])
                
        elif action_type == "scroll":
            pyautogui.scroll(data.get('amount', 0))

        return jsonify({"status": "success"})
    except Exception as e:
        logging.error(f"Action failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/exec', methods=['POST'])
def exec_code():
    """Runs Python/Powershell code locally."""
    # Implementation of local subprocess execution
    # Security Warning: This allows RCE by design (it's a sandbox)
    pass

if __name__ == '__main__':
    # Listen on all interfaces so the Docker host (WSL) can reach it
    app.run(host='0.0.0.0', port=5000)
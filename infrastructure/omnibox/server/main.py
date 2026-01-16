import os
import logging
import argparse
import subprocess
from flask import Flask, request, jsonify, send_file
import threading
import pyautogui
from PIL import Image
from io import BytesIO

app = Flask(__name__)
computer_control_lock = threading.Lock()
pyautogui.FAILSAFE = False

@app.route('/probe', methods=['GET'])
def probe_endpoint():
    return jsonify({"status": "Probe successful", "message": "Service is operational"}), 200

@app.route('/execute', methods=['POST'])
def execute_command():
    with computer_control_lock:
        data = request.json
        action_type = data.get("action_type")
        
        try:
            if action_type == "click":
                pyautogui.click(x=data['x'], y=data['y'], button=data.get('button', 'left'))
            elif action_type == "double_click":
                pyautogui.doubleClick(x=data['x'], y=data['y'])
            elif action_type == "type":
                if data.get('text'):
                    pyautogui.write(data['text'], interval=0.05)
                if data.get('keys'):
                    pyautogui.hotkey(*data['keys'])
            elif action_type == "scroll":
                 # OmniTool scroll logic
                 pyautogui.scroll(data.get('amount', 0))
                 
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/screenshot', methods=['GET'])
def capture_screen_with_cursor():    
    cursor_path = os.path.join(os.path.dirname(__file__), "cursor.png")
    screenshot = pyautogui.screenshot()
    
    # Overlay cursor (Visual Debugging)
    try:
        cursor_x, cursor_y = pyautogui.position()
        if os.path.exists(cursor_path):
            cursor = Image.open(cursor_path)
            cursor = cursor.resize((int(cursor.width / 1.5), int(cursor.height / 1.5)))
            screenshot.paste(cursor, (cursor_x, cursor_y), cursor)
    except:
        pass

    img_io = BytesIO()
    screenshot.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)


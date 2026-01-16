import os
import subprocess
import json
import time
import logging

logger = logging.getLogger("Session")

class SessionManager:
    def __init__(self, session_id: str):
        self.path = os.path.join("data", "raw_traces", session_id)
        os.makedirs(self.path, exist_ok=True)
        
        self.log_file = open(os.path.join(self.path, "events.jsonl"), "a", encoding="utf-8")
        self.video_path = os.path.join(self.path, "video.mp4")
        self.ffmpeg = None

    def start_recording(self):
        # ffmpeg reading raw bgra from stdin
        cmd = [
            'ffmpeg', '-y', 
            '-f', 'rawvideo', '-vcodec', 'rawvideo', '-s', '1920x1080', '-pix_fmt', 'bgra', '-r', '5',
            '-i', '-', 
            '-c:v', 'libx264', '-preset', 'ultrafast', '-qp', '0', 
            self.video_path
        ]
        self.ffmpeg = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write_video_frame(self, raw_bytes):
        if self.ffmpeg:
            try:
                self.ffmpeg.stdin.write(raw_bytes)
            except Exception as e:
                logger.error(f"Video write error: {e}")

    def log_event(self, event_data: dict):
        event_data['server_time'] = time.time()
        self.log_file.write(json.dumps(event_data) + "\n")
        self.log_file.flush()

    def close(self):
        if self.ffmpeg:
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait()
        self.log_file.close()

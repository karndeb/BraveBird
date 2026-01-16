import json
import cv2
import logging
import os
from typing import List, Dict, Tuple
from pathlib import Path

# Shared schemas
from shared.python.gui360_schema import RawTraceEvent

logger = logging.getLogger(__name__)

# Optimized Data Loader. 
# Instead of processing a massive video file, it uses the Event Log to perform Smart Keyframing

class TraceIngester:
    """
    Ingests a raw recording and performs 'Event-Based Keyframing'.
    Optimization: Discards 95% of video frames where no interaction occurred.
    """

    def __init__(self, trace_dir: str):
        self.trace_dir = Path(trace_dir)
        self.video_path = self.trace_dir / "video.mp4"
        self.log_path = self.trace_dir / "events.jsonl"
        
        if not self.video_path.exists() or not self.log_path.exists():
            raise FileNotFoundError(f"Invalid trace directory: {trace_dir}")

    def extract_keyframes(self) -> List[Dict]:
        """
        Scans the event log for clicks/types.
        Extracts ONLY the video frame at that exact timestamp (+/- buffer).
        Returns a list of {event, image_path} objects.
        """
        logger.info(f"🎞️ Extracting keyframes from {self.trace_dir}")
        
        events = []
        with open(self.log_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))

        # Filter for interaction events
        action_events = [e for e in events if e['type'] in ['click', 'keypress', 'scroll']]
        
        cap = cv2.VideoCapture(str(self.video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        keyframes = []
        
        for idx, event in enumerate(action_events):
            timestamp = event['timestamp']
            frame_id = int(timestamp * fps)
            
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = cap.read()
            
            if ret:
                # Save keyframe to disk (temporarily) for VLM consumption
                image_filename = f"action_{idx:03d}_{event['type']}.jpg"
                image_path = self.trace_dir / "processed" / image_filename
                os.makedirs(image_path.parent, exist_ok=True)
                
                cv2.imwrite(str(image_path), frame)
                
                keyframes.append({
                    "step_id": idx,
                    "event_data": event,
                    "image_path": str(image_path),
                    "timestamp": timestamp
                })
            else:
                logger.warning(f"⚠️ Could not read frame at {timestamp}s")

        cap.release()
        logger.info(f"✅ Extracted {len(keyframes)} keyframes from trace.")
        return keyframes
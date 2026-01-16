import logging
import json
import asyncio
from pathlib import Path
from typing import List, Dict
import numpy as np

# We reuse the Perception logic but in "Offline Mode"
from wsl_brain.actors.perception import PerceptionActor 
# We need to calculate Intersection over Union (IoU) or Distance
from wsl_brain.core.config import settings

logger = logging.getLogger(__name__)

# The Auditor. It replays user traces against the AI to find discrepancies.

class DataMiner:
    """
    Analyzes 'Golden Traces' (User Recordings).
    Checks if our current UI-Ins model would have predicted the same click.
    If NOT, it marks the frame as a 'Training Example'.
    """

    def __init__(self):
        # We use a direct HTTP client here instead of the Actor system 
        # to avoid polluting the live message bus.
        self.ui_ins_url = f"{settings.UI_INS_URL}/ground"
        self.failure_dir = Path("data/datasets/flywheel_failures")
        self.failure_dir.mkdir(parents=True, exist_ok=True)

    def calculate_distance(self, p1: tuple, p2: tuple) -> float:
        """Euclidean distance between two points."""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    async def mine_trace(self, trace_path: str):
        """
        Iterate through a user trace.
        For every click:
            1. Get User Coordinate (Ground Truth).
            2. Ask UI-Ins for Coordinate (Prediction).
            3. If distance > Threshold -> SAVE for training.
        """
        logger.info(f"⛏️ [DataMiner] Mining trace: {trace_path}")
        
        trace_dir = Path(trace_path)
        log_file = trace_dir / "events.jsonl"
        
        if not log_file.exists():
            logger.warning("Trace log missing.")
            return

        # Load events
        events = []
        with open(log_file, 'r') as f:
            for line in f:
                events.append(json.loads(line))

        click_events = [e for e in events if e['type'] == 'click']

        for i, event in enumerate(click_events):
            # Construct image path (assuming keyframer naming convention)
            # In a real impl, we'd look up the exact frame timestamp
            # For this snippet, we assume images are indexed.
            image_path = trace_dir / "processed" / f"action_{i:03d}_click.jpg"
            
            if not image_path.exists():
                continue

            user_x, user_y = event['x'], event['y']
            
            # The instruction usually comes from the audio transcript or the previous synthesizer pass
            # Here we assume a 'label' field exists or we generate a synthetic one
            instruction = event.get('metadata', {}).get('element_name', "target element")

            # Predict
            pred = await self._query_model(image_path, instruction)
            
            if not pred:
                continue

            pred_x, pred_y = pred
            
            # Check accuracy (Threshold: 50 pixels)
            dist = self.calculate_distance((user_x, user_y), (pred_x, pred_y))
            
            if dist > 50.0:
                logger.info(f"📉 [DataMiner] Discrepancy Found! User:({user_x},{user_y}) vs Model:({pred_x},{pred_y})")
                self._save_failure_case(image_path, instruction, (user_x, user_y), (pred_x, pred_y))
            else:
                logger.debug(f"✅ [DataMiner] Model match.")

    async def _query_model(self, img_path: Path, text: str):
        # Implementation of HTTP request to UI-Ins service
        # Returns (x, y) tuple
        pass

    def _save_failure_case(self, img_path, instruction, gt, pred):
        """Saves the data triplet for the Dataset Builder."""
        case_id = f"{int(time.time())}_{instruction.replace(' ', '_')}"
        save_path = self.failure_dir / case_id
        save_path.mkdir(exist_ok=True)
        
        # Copy image
        import shutil
        shutil.copy(img_path, save_path / "image.jpg")
        
        # Save metadata
        meta = {
            "instruction": instruction,
            "ground_truth": gt,
            "model_prediction": pred
        }
        with open(save_path / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)
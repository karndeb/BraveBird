import json
import logging
from pathlib import Path
from typing import List

from wsl_brain.core.config import settings

logger = logging.getLogger(__name__)

# The Editor. Formats raw failures into Qwen-VL compatible SFT data.

class DatasetBuilder:
    """
    Converts raw failure cases into the JSONL format required by Unsloth/Qwen-VL.
    Implements 'Thought Augmentation' using Gemini Flash.
    """

    def __init__(self):
        self.raw_dir = Path("data/datasets/flywheel_failures")
        self.output_file = Path("data/datasets/sft_train/bravebird_finetune.jsonl")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # We need a planner to generate synthetic thoughts
        # from wsl_brain.synthesizer.gemini_planner import WorkflowPlanner
        # self.planner = WorkflowPlanner() 

    async def build_dataset(self):
        logger.info("🏗️ [DatasetBuilder] Building fine-tuning dataset...")
        
        new_samples = []
        
        # Iterate over mined failures
        for case_dir in self.raw_dir.iterdir():
            if not case_dir.is_dir(): continue
            
            try:
                with open(case_dir / "metadata.json", 'r') as f:
                    meta = json.load(f)
                
                # We need to construct the Qwen-VL chat format
                # Concept from UI-Ins: "Instruction-as-Reasoning"
                # We ask Gemini to generate a "Thought" that EXPLAINS why the GT is correct.
                
                # synthetic_thought = await self.planner.generate_reasoning(...)
                synthetic_thought = f"I need to locate the {meta['instruction']}. Looking at the screen, it is located at coordinates {meta['ground_truth']}."

                sample = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image", "image": str(case_dir / "image.jpg")},
                                {"type": "text", "text": meta['instruction']}
                            ]
                        },
                        {
                            "role": "assistant",
                            "content": [
                                # The UI-Ins format: Thought -> Tool Call
                                {"type": "text", "text": f"<think>{synthetic_thought}</think>"},
                                {"type": "text", "text": f"<tool_call>{{'name': 'grounding', 'arguments': {{'action': 'click', 'coordinate': {list(meta['ground_truth'])}}}</tool_call>"}
                            ]
                        }
                    ]
                }
                
                new_samples.append(sample)
                
            except Exception as e:
                logger.error(f"Failed to process {case_dir}: {e}")

        # Write JSONL
        with open(self.output_file, 'w') as f:
            for sample in new_samples:
                f.write(json.dumps(sample) + "\n")
        
        logger.info(f"✅ [DatasetBuilder] Created {len(new_samples)} training samples.")
        return str(self.output_file)
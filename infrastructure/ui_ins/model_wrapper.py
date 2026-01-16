import os
import torch
import base64
import re
from io import BytesIO
from PIL import Image
from qwen_vl_utils import smart_resize
from vllm import LLM, SamplingParams
from transformers import Qwen2_5_VLProcessor

# Fix for vLLM multiprocessing issue
import multiprocessing as mp
try:
    mp.set_start_method('spawn', force=True)
except RuntimeError:
    pass

class CustomQwen2_5VL_VLLM_Model:
    """
    Wrapper for Qwen2.5-VL using vLLM backend.
    Optimized for UI Grounding tasks with smart resizing.
    """
    
    def __init__(self, model_path="Qwen/Qwen2.5-VL-7B-Instruct", max_pixels=12845056):
        self.model_path = model_path
        self.max_pixels = max_pixels
        self.model = None
        self.processor = None

    def load_model(self):
        """Initializes the vLLM engine."""
        print(f"🚀 Loading vLLM model: {self.model_path}")
        
        self.model = LLM(
            model=self.model_path,
            limit_mm_per_prompt={"image": 1},
            trust_remote_code=True,
            dtype="auto",
            # Adjust based on available GPUs in the Bravebird machine
            tensor_parallel_size=torch.cuda.device_count(), 
            gpu_memory_utilization=0.90,
            max_model_len=8192, # Adjusted for typical UI task context
            mm_processor_kwargs={
                "min_pixels": 28 * 28,
                "max_pixels": self.max_pixels,
            },
        )
        # We need the processor for chat template construction
        self.processor = Qwen2_5_VLProcessor.from_pretrained(self.model_path, trust_remote_code=True)
        print("✅ vLLM Model loaded.")

    def parse_coordinates(self, raw_string: str):
        """Extracts coordinates from model output: [x,y]"""
        matches = re.findall(r'\[(\d+),(\d+)\]', raw_string)
        matches = [tuple(map(int, match)) for match in matches]
        if len(matches) == 0:
            return None
        return matches[0]

    def ground(self, instruction: str, base64_image: str) -> dict:
        """
        Main inference method.
        Returns normalized coordinates.
        """
        # 1. Decode Image
        image_data = base64.b64decode(base64_image)
        image = Image.open(BytesIO(image_data)).convert('RGB')

        # 2. Smart Resize
        resized_height, resized_width = smart_resize(
            image.height,
            image.width,
            factor=14 * 2,
            min_pixels=28 * 28,
            max_pixels=self.max_pixels,
        )
        resized_image = image.resize((resized_width, resized_height))

        # 3. Construct Prompt (UI-Ins System Prompt)
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are a helpful assistant."},
                    {"type": "text", "text": """You are a GUI agent... (omitted full prompt for brevity, insert full UI-INS prompt here)..."""}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": resized_image},
                    {"type": "text", "text": instruction}
                ]
            }
        ]

        # 4. Prepare Inputs
        # Manual template application to support vLLM input format
        prompt_text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # Inject "Guide Text" to force structured tool call
        guide_text = "<tool_call>\n{\"name\": \"grounding\", \"arguments\": {\"action\": \"click\", \"coordinate\": ["
        full_prompt = prompt_text + guide_text

        # 5. Generate
        sampling_params = SamplingParams(temperature=0.0, max_tokens=128, stop=["}", "]"])
        
        inputs = [{
            "prompt": full_prompt,
            "multi_modal_data": {"image": resized_image}
        }]
        
        outputs = self.model.generate(inputs, sampling_params=sampling_params)
        raw_output = outputs[0].outputs[0].text.strip()
        
        # 6. Parse Result
        # Reconstruct valid JSON fragment to parse coords
        full_response_str = f"[{raw_output}]" # Closing the array
        
        coords = self.parse_coordinates(full_response_str)
        
        if coords:
            px, py = coords
            # Return normalized coordinates (0.0 to 1.0)
            return {
                "point": [px / resized_width, py / resized_height],
                "raw": raw_output
            }
        
        return {"point": None, "raw": raw_output}
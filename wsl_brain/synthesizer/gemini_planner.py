import logging
import json
from typing import List, Dict

# Hypothetical wrapper for Google GenAI SDK
from wsl_brain.core.actors.cognition import GeminiClient 
from wsl_brain.core.config import settings

logger = logging.getLogger(__name__)

# The Generalist. Uses Gemini Flash to understand Intent.

PLANNER_SYSTEM_PROMPT = """
You are an expert Robotic Process Automation (RPA) planner. 
You are analyzing a video trace of a human performing a task on a computer.
Your goal is to convert this trace into a generalized, robust workflow.

INPUT:
1. A sequence of Keyframes (Screenshots).
2. A sequence of Actions (Clicks/Types) associated with those frames.
3. Verified Element Metadata (from OmniParser).

OUTPUT:
A JSON plan following the GUI-360 schema. 
If the user typed text, identify if it should be a VARIABLE parameter.
Example: If user typed "Sushi", generalize it to {{search_query}}.
"""

class WorkflowPlanner:
    def __init__(self):
        self.llm = GeminiClient(model=settings.GEMINI_MODEL_NAME)

    async def generate_plan(self, keyframes: List[Dict], verified_metadata: List[Dict]) -> Dict:
        """
        Sends the multimodal context to Gemini to generate the abstract plan.
        """
        logger.info("🧠 Sending trace context to Gemini for Planning...")
        
        # Construct Multimodal Prompt
        prompt_content = [PLANNER_SYSTEM_PROMPT]
        
        for i, frame in enumerate(keyframes):
            meta = verified_metadata[i]
            
            # Text description of the event
            action_desc = f"Step {i}: {frame['event_data']['type']} at {frame['event_data']['x']},{frame['event_data']['y']}"
            if meta['verified']:
                action_desc += f" (Interacted with: {meta['element_name']})"
            
            prompt_content.append(action_desc)
            prompt_content.append(frame['image_path']) # Gemini SDK handles file paths

        prompt_content.append("\nGenerate the JSON workflow:")

        # Call LLM
        response = await self.llm.generate(prompt_content, json_mode=True)
        
        try:
            plan = json.loads(response)
            logger.info("✅ Plan generated successfully.")
            return plan
        except json.JSONDecodeError:
            logger.error("❌ Failed to parse Gemini response as JSON")
            raise
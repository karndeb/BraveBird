import logging
import json
import base64
from typing import Dict, Tuple

from wsl_brain.core.config import settings
# Assuming we reuse the LMMAgent wrapper we defined in core logic
from wsl_brain.core.actors.cognition import LMMAgent 

logger = logging.getLogger(__name__)

# The Judge. Implements the evaluation logic inspired by the GUI-360° EvaAgent.

EVA_SYSTEM_PROMPT = """
You are Eva, an impartial automated evaluator for GUI automation tasks.
Your job is to verify if a computer agent successfully completed a user's request based on the final screen state.

INPUT:
1. User Request (The Goal).
2. Final Screenshot.
3. Accessibility Tree (Metadata about UI elements).

CRITERIA:
- Verification must be strict. "Close enough" is a FAIL.
- Rely on visual evidence (e.g., "Is the file 'report.pdf' visible?") AND structural evidence (A11y tree).
- If the task involved data extraction, check if the data exists in the output field.

OUTPUT FORMAT:
Return a JSON object:
{
    "success": boolean,
    "confidence": float (0.0 to 1.0),
    "reasoning": "string explanation",
    "missing_elements": ["list", "of", "missing", "things"]
}
"""

class EvaAgent:
    def __init__(self):
        self.agent = LMMAgent(
            engine_params={
                "engine_type": "gemini",
                "api_key": settings.GEMINI_API_KEY,
                "model": settings.GEMINI_MODEL_NAME
            },
            system_prompt=EVA_SYSTEM_PROMPT
        )

    async def evaluate(self, task_instruction: str, screenshot_bytes: bytes, a11y_tree: str = "") -> Dict:
        """
        Evaluates the success of a task execution.
        """
        logger.info(f"🕵️ [EvaAgent] Evaluating task: '{task_instruction}'")

        self.agent.reset()
        
        # Construct the context
        user_message = f"User Request: {task_instruction}\n\n"
        if a11y_tree:
            # Truncate tree if too large to save tokens
            user_message += f"Final Accessibility Tree Snippet:\n{a11y_tree[:4000]}\n"
        
        # Add message with image
        self.agent.add_message(
            text_content=user_message,
            image_content=screenshot_bytes, # LMMAgent handles base64 conversion
            role="user"
        )

        try:
            # Call Gemini
            # force json mode in prompt is usually enough, but some providers support response_format
            response_text = self.agent.get_response(temperature=0.0)
            
            # Clean formatting (remove markdown code blocks if present)
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_json)
            
            log_level = logging.INFO if result['success'] else logging.WARNING
            logger.log(log_level, f"🕵️ [EvaAgent] Verdict: {'✅ PASS' if result['success'] else '❌ FAIL'}. Reason: {result['reasoning']}")
            
            return result

        except json.JSONDecodeError:
            logger.error(f"❌ [EvaAgent] Failed to parse JSON response: {response_text}")
            return {"success": False, "reasoning": "Evaluator output malformed", "confidence": 0.0}
        except Exception as e:
            logger.error(f"❌ [EvaAgent] Evaluation failed: {e}")
            return {"success": False, "reasoning": f"System Error: {str(e)}", "confidence": 0.0}
        
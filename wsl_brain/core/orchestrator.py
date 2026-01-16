import logging
import json
import asyncio
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from wsl_brain.core.config import settings
from wsl_brain.core.prompts import (
    PLANNING_PROMPT,
    LEDGER_PROMPT,
    SYSTEM_PROMPT_WINDOWS,
    CODE_GENERATION_PROMPT
)
# We assume a generic LLM wrapper (Gemini) is available
from wsl_brain.actors.cognition import GeminiClient

logger = logging.getLogger("Orchestrator")

class BrainOrchestrator:
    """
    The High-Level Controller.
    Implements the 'Orchestrated Agent' pattern:
    1. Plan (Initial)
    2. Ledger (Per Step Progress)
    3. Action (GUI or Code)
    """

    def __init__(self):
        self.llm = GeminiClient()
        self.task_instruction = ""
        self.plan = None
        self.ledger = None
        self.step_count = 0
        
        # Context Management
        self.history: List[Dict] = []
        self.max_images_in_context = 2

    async def initialize_task(self, instruction: str):
        """
        Step 0: Generate the initial plan.
        """
        self.task_instruction = instruction
        self.step_count = 0
        self.history = []
        
        logger.info(f"🧠 Generating Plan for: {instruction}")
        
        # 1. Construct Planning Prompt
        prompt = PLANNING_PROMPT.format(task=instruction)
        
        # 2. Call Gemini
        response = await self.llm.generate_text(prompt, json_mode=True)
        self.plan = json.loads(response)
        
        # 3. Add Plan to History
        self._add_to_history("assistant", f"Plan generated: {json.dumps(self.plan)}")
        logger.info(f"📋 Plan: {self.plan}")

    async def decide_next_step(self, screen_state: Dict) -> Dict:
        """
        The Main Loop.
        Returns the Action JSON to be executed.
        """
        self.step_count += 1
        
        # 1. Update Progress Ledger
        await self._update_ledger()

        # 2. Construct the Vision-Language Prompt
        screen_info_text = screen_state.get("screen_info", "") # From OmniParser
        
        system_prompt = SYSTEM_PROMPT_WINDOWS.format(
            screen_info=screen_info_text
        )
        
        # 3. Prepare Context (With Image Filtering)
        context_messages = self._build_context_for_inference(screen_state)

        # 4. Call Gemini
        logger.info(f"🤔 Thinking (Step {self.step_count})...")
        response = await self.llm.generate_chat(
            system_instruction=system_prompt,
            messages=context_messages,
            json_mode=True
        )
        
        action_json = json.loads(response)
        
        # 5. Save Decision to History
        self._add_to_history("assistant", json.dumps(action_json))
        
        return action_json

    async def _update_ledger(self):
        """
        Self-Reflection Step. Checks if we are stuck or finished.
        """
        if self.step_count == 1: return # Skip on first step

        prompt = LEDGER_PROMPT.format(task=self.task_instruction)
        
        # We send a text-only history for the ledger update to save tokens/time
        # (The ledger logic mainly needs the action history, not the screenshots)
        text_history = [m for m in self.history if m.get("type") == "text"]
        text_history.append({"role": "user", "content": prompt})
        
        response = await self.llm.generate_chat(messages=text_history, json_mode=True)
        self.ledger = json.loads(response)
        
        satisfied = self.ledger.get("is_request_satisfied", {}).get("answer", False)
        is_loop = self.ledger.get("is_in_loop", {}).get("answer", False)
        
        logger.info(f"📊 Ledger: Satisfied={satisfied}, Loop={is_loop}")
        
        # Inject ledger insight into the main history so the Agent 'knows' its status
        self._add_to_history("assistant", f"Progress Ledger Update: {response}")

    def _build_context_for_inference(self, screen_state: Dict) -> List[Dict]:
        """
        Constructs the message payload.
        CRITICAL OPTIMIZATION: Removes old images to prevent context overflow.
        """
        # 1. Filter existing history (Keep text, drop old images)
        optimized_history = []
        image_count = 0
        
        # Iterate backwards to keep the newest images
        for msg in reversed(self.history):
            if msg.get("type") == "image":
                if image_count < self.max_images_in_context:
                    optimized_history.insert(0, msg)
                    image_count += 1
                # Else: Skip (Drop old image)
            else:
                optimized_history.insert(0, msg)
        
        # 2. Add CURRENT Observation
        # (This is the fresh data from Perception Actor)
        current_obs = [
            {"role": "user", "type": "image", "content": screen_state['base64_image']},
            {"role": "user", "type": "text", "content": f"Observation: Screen parsed. UI Tree available. Ledger status: {json.dumps(self.ledger)}"}
        ]
        
        return optimized_history + current_obs

    def _add_to_history(self, role: str, content: str, msg_type: str = "text"):
        self.history.append({
            "role": role,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })


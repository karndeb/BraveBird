import json
import logging
import re
from typing import List, Dict, Tuple
from wsl_brain.core.prompts import PLANNING_PROMPT_TEMPLATE, LEDGER_PROMPT_TEMPLATE, SYSTEM_PROMPT_WINDOWS
from wsl_brain.core.config import settings

logger = logging.getLogger("Orchestrator")

class VLMOrchestratedAgent:
    """
    Implements the OmniTool Orchestration Logic:
    1. Initial Planning
    2. Step-wise Ledger Updates (Progress Tracking)
    3. Token Management (Image Filtering)
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.task = ""
        self.plan = None
        self.ledger = None
        self.step_count = 0
        self.max_images = 2  # As per OmniTool default

    async def step(self, messages: List[Dict], parsed_screen: Dict) -> Tuple[Dict, str]:
        """
        Main decision step.
        Returns: (Action_JSON, System_Prompt_Used)
        """
        # 1. Initialize Task & Plan (First Step)
        if self.step_count == 0:
            # The first message from user is the task
            self.task = messages[0]["content"][0]["text"]
            await self._generate_initial_plan(messages)

        # 2. Update Ledger (Subsequent Steps)
        else:
            await self._update_ledger(messages)

        # 3. Context Management (Token Optimization)
        # Remove old SOM images to save tokens
        optimized_messages = self._filter_message_history(messages)

        # 4. Construct System Prompt with Screen Info
        # OmniParser V2 output injection
        screen_info = parsed_screen.get("screen_info", "")
        system_prompt = SYSTEM_PROMPT_WINDOWS.format(screen_info=screen_info)

        # 5. Call LLM
        response = await self.llm.generate(
            messages=optimized_messages,
            system_instruction=system_prompt,
            json_mode=True
        )

        self.step_count += 1
        return json.loads(response), system_prompt

    async def _generate_initial_plan(self, messages):
        prompt = PLANNING_PROMPT_TEMPLATE.format(task=self.task)
        # Temporary message for planning
        plan_msgs = messages + [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        
        response = await self.llm.generate(plan_msgs, json_mode=True)
        self.plan = json.loads(response)
        logger.info(f"📋 Generated Plan: {self.plan}")
        
        # Inject plan into history
        messages.append({"role": "assistant", "content": [{"type": "text", "text": f"Plan: {response}"}]})

    async def _update_ledger(self, messages):
        prompt = LEDGER_PROMPT_TEMPLATE.format(task=self.task)
        ledger_msgs = messages + [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        
        response = await self.llm.generate(ledger_msgs, json_mode=True)
        self.ledger = json.loads(response)
        
        # Log progress
        satisfied = self.ledger.get("is_request_satisfied", {}).get("answer", False)
        logger.info(f"📊 Ledger Update: Satisfied={satisfied}")
        
        # Inject ledger into history
        messages.append({"role": "assistant", "content": [{"type": "text", "text": f"Ledger: {response}"}]})

    def _filter_message_history(self, messages):
        """
        Removes old screenshots to prevent context window overflow.
        Keeps only the last N images.
        """
        # Count images
        total_images = sum(1 for m in messages for c in m["content"] if c["type"] == "image_url")
        to_remove = total_images - self.max_images

        if to_remove <= 0:
            return messages

        filtered_messages = []
        for msg in messages:
            new_content = []
            for block in msg["content"]:
                if block["type"] == "image_url":
                    if to_remove > 0:
                        to_remove -= 1
                        continue # Skip this image (delete it)
                new_content.append(block)
            filtered_messages.append({"role": msg["role"], "content": new_content})
            
        return filtered_messages

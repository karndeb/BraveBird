import logging
from wsl_brain.actors.base_actor import BaseActor
from wsl_brain.core.orchestration_logic import VLMOrchestratedAgent
from shared.python.events_pb2 import UserTranscriptEvent, WorkflowStartEvent, GroundingResultEvent

logger = logging.getLogger(__name__)

# The "Brain". Wraps AgentS3Controller and manages the High-Level Loop.

class CognitionActor(BaseActor):
    """
    The Brain.
    Manages the 'Cognitive State' and decides the next move using Agent S3 logic.
    """

    def __init__(self, bus):
        super().__init__(bus, name="CognitionActor")
        self.agent = VLMOrchestratedAgent(llm_client=GeminiClient())
        self.current_goal = None
        self.message_history = []

    async def setup(self):
        # Listen for User Voice commands
        await self.bus.subscribe("cognition.user_voice", UserTranscriptEvent, self.on_user_voice)
        # Listen for Workflow starts (from Synthesizer)
        await self.bus.subscribe("cognition.start_workflow", WorkflowStartEvent, self.on_workflow_start)
        # Listen for Grounding results to continue the loop
        await self.bus.subscribe("perception.grounding_result", GroundingResultEvent, self.on_grounding_result)

    async def cleanup(self):
        pass

    async def on_user_voice(self, event: UserTranscriptEvent):
        """
        User said something. Is it a command?
        """
        logger.info(f"[{self.name}] User said: {event.text}")
        
        # Simple heuristic or LLM router here
        if "stop" in event.text.lower():
            logger.critical(f"[{self.name}] EMERGENCY STOP triggered via Voice.")
            # Emit Stop Event

    async def on_workflow_start(self, event: WorkflowStartEvent):
        """
        Synthesizer finished creating a plan. Let's execute it.
        """
        logger.info(f"[{self.name}] Starting workflow: {event.workflow_id}")
        self.controller.load_workflow(event.workflow_json)
        
        # Trigger first step
        await self._execute_next_step()

    async def _execute_next_step(self):
        # 1. Get Visual State from Perception (contains OmniParser info)
        # Note: We assume PerceptionActor now returns 'parsed_screen' object
        # matching OmniTool format (screen_info string + bbox list)
        
        # 2. Run Orchestrator Step
        action_json, sys_prompt = await self.agent.step(
            self.message_history, 
            self.current_parsed_screen
        )

        # 3. Handle Result
        if action_json.get("Next Action") == "None":
            logger.info("✅ Task Completed according to Agent.")
            # Trigger Evaluation
        else:
            # Dispatch Action
            await self.bus.publish_action(action_json)

    async def on_grounding_result(self, event: GroundingResultEvent):
        """
        Perception Actor found the coordinates. Now we act.
        """
        if event.confidence < 0.5:
            logger.warning(f"[{self.name}] Low confidence grounding. Retrying logic...")
            # Handle failure logic
            return

        logger.info(f"[{self.name}] Grounding success. Executing click at {event.x}, {event.y}")
        
        # Create Action Event
        action = self.controller.create_click_action(event.x, event.y)
        await self.bus.publish_action_request(action)
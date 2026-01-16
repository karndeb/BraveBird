import asyncio
import logging
from .ingest import TraceIngester
from .omniparser_verifier import ElementVerifier
from .gemini_planner import WorkflowPlanner
from .schema_builder import save_workflow

logger = logging.getLogger(__name__)

# The Entry Point for this module.

class SynthesizerEngine:
    def __init__(self):
        self.verifier = ElementVerifier()
        self.planner = WorkflowPlanner()

    async def process_trace(self, trace_path: str, output_name: str):
        # 1. Ingest & Keyframe
        ingester = TraceIngester(trace_path)
        keyframes = ingester.extract_keyframes()
        
        # 2. Verify Elements (The Specialist Loop)
        verified_meta = []
        for frame in keyframes:
            if 'x' in frame['event_data']:
                coords = (frame['event_data']['x'], frame['event_data']['y'])
                meta = self.verifier.verify_click(frame['image_path'], coords)
                verified_meta.append(meta)
            else:
                verified_meta.append({"verified": False})

        # 3. Plan (The Generalist Loop)
        raw_plan = await self.planner.generate_plan(keyframes, verified_meta)
        
        # 4. Save
        save_workflow(raw_plan, output_name)
        logger.info(f"🎉 Workflow {output_name} synthesis complete!")
from .perception import PerceptionActor
from .audio import AudioActor
from .action import ActionActor
from .cognition import CognitionActor

__all__ = ["PerceptionActor", "AudioActor", "ActionActor", "CognitionActor"]

'''
The scripts in this module implements the Async-Actor Model. 
They operate independently, communicating solely through the EventBus. 
This decoupling allows the Vision system to process frames while the Brain is thinking, and allows the Audio system to transcribe voice commands in parallel.
'''
from .gui360_schema import (
    Workflow, 
    ExecutionStep, 
    StepAction, 
    ActionType, 
    AgentThought,
    ElementMetadata,
    FineTuningSample
)

# In production, these import the actual generated pb2 classes
# from .events_pb2 import BusEvent, VisualFrame, UserInteraction, AgentAction

__all__ = [
    "Workflow",
    "ExecutionStep",
    "StepAction",
    "ActionType",
    "AgentThought",
    "ElementMetadata",
    "FineTuningSample"
]

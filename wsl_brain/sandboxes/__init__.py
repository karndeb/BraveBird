from .base import SandboxEnv
from .arrakis_client import ArrakisSandbox
from .omnibox_client import OmniBoxSandbox
from .win_bridge_client import WindowsBridgeSandbox

def get_sandbox(name: str, config: dict) -> SandboxEnv:
    if name == "arrakis":
        return ArrakisSandbox(config)
    elif name == "omnibox":
        return OmniBoxSandbox(config)
    elif name == "windows":
        return WindowsBridgeSandbox(config)
    else:
        raise ValueError(f"Unknown sandbox type: {name}")

__all__ = ["get_sandbox", "SandboxEnv", "ArrakisSandbox", "OmniBoxSandbox", "WindowsBridgeSandbox"]

'''
Factory pattern for easy instantiation.
This module implements the Adapter Pattern to unify disparate execution environments (Linux MicroVMs, Windows Docker, and Native Windows) under a single, robust interface. 
This allows the high-level Agent logic to be OS-agnostic.
'''

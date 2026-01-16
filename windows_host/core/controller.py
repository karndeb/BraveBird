import logging
import pyautogui
import time
from typing import Dict, List, Optional

logger = logging.getLogger("WindowsController")

# The "Hands".
# This class wraps pyautogui to physically control the Windows OS. It acts as the actuation layer when the system is in Execution Mode.

class WindowsController:
    """
    Actuator for Native Windows Control.
    Executes actions requested by the WSL Brain.
    
    Safety: Includes Fail-Safes to prevent the agent from taking over the mouse uncontrollably.
    """

    def __init__(self):
        # Fail-Safe: Moving mouse to (0,0) kills the script
        pyautogui.FAILSAFE = True
        # Small pause between actions for stability
        pyautogui.PAUSE = 0.1
        logger.info("🦾 Windows Controller Initialized.")

    def execute_click(self, x: int, y: int, button: str = "left", double: bool = False):
        """Executes a mouse click."""
        try:
            # Ensure coordinates are within screen bounds
            screen_w, screen_h = pyautogui.size()
            safe_x = max(0, min(x, screen_w - 1))
            safe_y = max(0, min(y, screen_h - 1))
            
            logger.info(f"🖱️ Clicking {button} at ({safe_x}, {safe_y}) [Double: {double}]")
            
            if double:
                pyautogui.doubleClick(x=safe_x, y=safe_y, button=button)
            else:
                pyautogui.click(x=safe_x, y=safe_y, button=button)
                
        except pyautogui.FailSafeException:
            logger.critical("🚨 FAILSAFE TRIGGERED. Stopping execution.")
            raise
        except Exception as e:
            logger.error(f"❌ Click failed: {e}")

    def execute_type(self, text: Optional[str], keys: Optional[List[str]]):
        """Executes keyboard input."""
        try:
            if text:
                logger.info(f"⌨️ Typing text: '{text}'")
                # interval=0.01 simulates human typing speed slightly
                pyautogui.write(text, interval=0.01)
            
            if keys:
                logger.info(f"⌨️ Pressing keys: {keys}")
                # Handle combos like ['ctrl', 'c']
                pyautogui.hotkey(*keys)
                
        except Exception as e:
            logger.error(f"❌ Keyboard action failed: {e}")

    def execute_scroll(self, amount: int):
        """Executes scrolling."""
        try:
            logger.info(f"📜 Scrolling {amount}")
            pyautogui.scroll(amount)
        except Exception as e:
            logger.error(f"❌ Scroll failed: {e}")

    def get_screen_size(self):
        return pyautogui.size()
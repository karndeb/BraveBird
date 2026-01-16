import logging
import time
import threading
from pynput import mouse, keyboard
from typing import Optional

from windows_host.core.bus_producer import BusProducer
from windows_host.capture.accessibility import AccessibilityScraper
from shared.python.events_pb2 import UserInteraction, MouseEvent, KeyboardEvent, A11yNode

logger = logging.getLogger("InputListener")

# The "Nervous System".
# Uses pynput to intercept hardware events. Crucially, it orchestrates the AccessibilityScraper. When a click happens, it pauses momentarily to dispatch the scrape request, ensuring the metadata is tied to the click event.

class InputListener:
    """
    Global Hook for Mouse and Keyboard events.
    Combines raw input with Accessibility Data.
    """

    def __init__(self, bus: BusProducer, session_manager=None):
        self.bus = bus
        self.scraper = AccessibilityScraper()
        self.session = session_manager
        self.mouse_listener = None
        self.key_listener = None
        
        # Debouncing logic
        self.last_click_time = 0
        self.last_scroll_time = 0

    def start(self):
        logger.info("👂 Starting Input Listeners...")
        
        self.mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self.key_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        
        self.mouse_listener.start()
        self.key_listener.start()

    def stop(self):
        if self.mouse_listener: self.mouse_listener.stop()
        if self.key_listener: self.key_listener.stop()
        self.scraper.shutdown()
        logger.info("👂 Input Listeners stopped.")

    def _on_click(self, x, y, button, pressed):
        """
        Triggered when mouse button is clicked.
        We only care about 'Release' events to signify a completed action,
        BUT we grab accessibility data on 'Press' to ensure UI hasn't changed yet.
        """
        if not pressed: # On release (Action confirmed)
            return

        # Debounce micro-clicks
        now = time.time()
        if now - self.last_click_time < 0.05:
            return
        self.last_click_time = now

        timestamp = int(now * 1000)
        btn_name = str(button).replace('Button.', '')

        logger.info(f"🖱️ Click detected at ({x}, {y})")

        # 1. Prepare Basic Event
        interaction = UserInteraction()
        interaction.timestamp = timestamp
        interaction.mouse.timestamp = timestamp
        interaction.mouse.type = "click"
        interaction.mouse.x = x
        interaction.mouse.y = y
        interaction.mouse.button = btn_name

        # ... setup event dict ...
        event_dict = {
            "type": "mouse", "action": "click", "x": x, "y": y, 
            "button": str(button), "timestamp": timestamp
        }

        # --- CHANGED HERE ---
        if self.session:
            self.session.log_event(event_dict)
        # --------------------

        # 2. Enrich with A11y Data (Async)
        # We define a callback to publish the event once scraping is done
        def on_scrape_complete(node: Optional[A11yNode]):
            if node:
                interaction.accessibility_context.CopyFrom(node)
                # Fallback: if name is empty, try to get window title
                if not node.name:
                    try:
                        import pygetwindow
                        win = pygetwindow.getWindowsAt(x, y)
                        if win:
                            interaction.active_window_title = win[0].title
                    except: pass
            
            # Publish to Bus
            self.bus.publish("input.interaction", interaction)

        # Trigger Scraper
        self.scraper.scrape_at(x, y, on_scrape_complete)

    def _on_scroll(self, x, y, dx, dy):
        """Rate-limited scroll logging."""
        now = time.time()
        if now - self.last_scroll_time < 0.2: # Limit to 5hz
            return
        self.last_scroll_time = now

        interaction = UserInteraction()
        interaction.timestamp = int(now * 1000)
        interaction.mouse.type = "scroll"
        interaction.mouse.x = x
        interaction.mouse.y = y
        interaction.mouse.scroll_delta = dy
        
        self.bus.publish("input.interaction", interaction)

    def _on_key_press(self, key):
        """Log key presses."""
        try:
            k = key.char
        except AttributeError:
            k = str(key).replace('Key.', '')

        interaction = UserInteraction()
        interaction.timestamp = int(time.time() * 1000)
        interaction.keyboard.type = "press"
        interaction.keyboard.key = k
        
        # We don't scrape A11y on typing usually, too slow
        self.bus.publish("input.interaction", interaction)
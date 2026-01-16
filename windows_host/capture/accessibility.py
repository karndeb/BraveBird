import logging
import json
import concurrent.futures
from typing import Dict, Optional
from pywinauto import Desktop, UIAError

from shared.python.events_pb2 import A11yNode

logger = logging.getLogger("AccessibilityScraper")

# The "Touch".
# This uses pywinauto (which wraps Windows UI Automation) to inspect elements.
# Performance Note: UIA calls can be slow (50ms - 500ms). We use a Thread Pool to prevent blocking the input listener.

class AccessibilityScraper:
    """
    Retrieves semantic metadata about UI elements under the cursor.
    Uses Windows UI Automation (UIA) API.
    """

    def __init__(self):
        self.desktop = Desktop(backend="uia")
        # Thread pool to avoid blocking the main input hook thread
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def scrape_at(self, x: int, y: int, callback):
        """
        Async request to scrape element at (x, y).
        Results are passed to the callback function.
        """
        self.executor.submit(self._do_scrape, x, y, callback)

    def _do_scrape(self, x: int, y: int, callback):
        """
        Heavy lifting: UIA traversal.
        """
        try:
            # Get element at point
            wrapper = self.desktop.from_point(x, y)
            
            if wrapper:
                node = A11yNode()
                node.name = wrapper.window_text() or ""
                node.control_type = wrapper.element_info.control_type or "Unknown"
                node.automation_id = wrapper.element_info.automation_id or ""
                node.is_enabled = wrapper.is_enabled()
                
                rect = wrapper.rectangle()
                node.bbox.extend([rect.left, rect.top, rect.right, rect.bottom])
                
                # logger.debug(f"🔍 Scraped: {node.name} ({node.control_type})")
                callback(node)
            else:
                callback(None)

        except UIAError:
            # Element might have disappeared or moved
            callback(None)
        except Exception as e:
            logger.error(f"❌ Scraper error: {e}")
            callback(None)
            
    def shutdown(self):
        self.executor.shutdown(wait=False)
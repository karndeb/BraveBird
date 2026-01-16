import logging
import requests
import base64
from typing import Dict, Optional, Tuple

from wsl_brain.core.config import settings

logger = logging.getLogger(__name__)

# The Specialist. 
# Uses OmniParser V2 to validate what Gemini thinks it sees.

class ElementVerifier:
    """
    Uses OmniParser V2 (Microservice) to spatially verify elements.
    """
    
    def __init__(self):
        self.api_url = f"{settings.OMNIPARSER_URL}/parse/"

    def verify_click(self, image_path: str, click_coords: Tuple[int, int]) -> Dict:
        """
        1. Sends image to OmniParser.
        2. Checks which detected bounding box contains the click_coords.
        3. Returns the semantic label (e.g. 'Save Button') and confidence.
        """
        logger.debug(f"🔍 Verifying element at {click_coords}")
        
        # 1. Encode Image
        with open(image_path, "rb") as img_file:
            b64_image = base64.b64encode(img_file.read()).decode('utf-8')

        # 2. Call Microservice
        try:
            response = requests.post(self.api_url, json={"base64_image": b64_image})
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"❌ OmniParser service failed: {e}")
            return {"verified": False, "reason": "Service Unavailable"}

        # 3. Hit Test (Geometry)
        # Note: OmniParser returns normalized [0,1] coordinates or pixels depending on config.
        # Assuming pixels here based on our config.
        cx, cy = click_coords
        elements = data['parsed_content_list']
        
        matched_element = None
        min_area = float('inf')

        for el in elements:
            bbox = el['bbox'] # [x1, y1, x2, y2]
            if bbox[0] <= cx <= bbox[2] and bbox[1] <= cy <= bbox[3]:
                # If multiple boxes overlap (e.g. text inside button), pick smaller one
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                if area < min_area:
                    min_area = area
                    matched_element = el

        if matched_element:
            logger.info(f"✅ Verified Click: User clicked '{matched_element['content']}' ({matched_element['type']})")
            return {
                "verified": True,
                "element_name": matched_element['content'],
                "element_type": matched_element['type'],
                "bbox": matched_element['bbox']
            }
        
        logger.warning(f"⚠️ No element found at {click_coords} by OmniParser.")
        return {"verified": False, "reason": "No Element Detected"}
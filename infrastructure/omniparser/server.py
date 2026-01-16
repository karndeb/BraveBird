"""
OmniParser V2 Inference Service.
Wraps YOLO (Icon Detection) and Florence-2 (Captioning) into a FastAPI endpoint.
"""
import sys
import os
import time
import logging
import argparse
import base64
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import torch

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OmniParserService")

# Add current directory to path to find 'util' package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import OmniParser utilities (Assumes 'util/' is present in the docker context)
try:
    from util.omniparser import Omniparser
except ImportError:
    logger.critical("❌ Could not import 'util.omniparser'. Ensure OmniParser utils are present.")
    sys.exit(1)

class ParseRequest(BaseModel):
    base64_image: str

class ParseResponse(BaseModel):
    som_image_base64: str
    parsed_content_list: list
    latency: float

app = FastAPI(title="OmniParser V2 Service")
omniparser: Omniparser = None

def load_model(args):
    global omniparser
    logger.info("🚀 Loading OmniParser models...")
    
    config = {
        'som_model_path': args.som_model_path,
        'caption_model_name': args.caption_model_name,
        'caption_model_path': args.caption_model_path,
        'device': args.device,
        'BOX_TRESHOLD': args.box_threshold
    }
    
    try:
        omniparser = Omniparser(config)
        logger.info("✅ OmniParser models loaded successfully.")
    except Exception as e:
        logger.critical(f"❌ Failed to load models: {e}")
        sys.exit(1)

@app.post("/parse/", response_model=ParseResponse)
async def parse(request: ParseRequest):
    if not omniparser:
        raise HTTPException(status_code=503, detail="Model not initialized")

    logger.info("Processing parsing request...")
    start_time = time.time()
    
    try:
        # Run Inference
        dino_labeled_img, parsed_content_list = omniparser.parse(request.base64_image)
        
        latency = time.time() - start_time
        logger.info(f"✅ Parsing complete in {latency:.4f}s. Found {len(parsed_content_list)} elements.")
        
        return {
            "som_image_base64": dino_labeled_img, 
            "parsed_content_list": parsed_content_list, 
            "latency": latency
        }
    except Exception as e:
        logger.error(f"❌ Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probe/")
async def health_check():
    if omniparser:
        return {"status": "ready", "device": "cuda" if torch.cuda.is_available() else "cpu"}
    return {"status": "loading"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Omniparser API')
    # Default paths map to the Docker volume mount point
    parser.add_argument('--som_model_path', type=str, default='/app/weights/icon_detect/model.pt')
    parser.add_argument('--caption_model_name', type=str, default='florence2')
    parser.add_argument('--caption_model_path', type=str, default='/app/weights/icon_caption_florence')
    parser.add_argument('--device', type=str, default='cuda')
    parser.add_argument('--box_threshold', type=float, default=0.05)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    
    args = parser.parse_args()
    
    # Load model before starting server
    load_model(args)
    
    uvicorn.run(app, host=args.host, port=args.port)
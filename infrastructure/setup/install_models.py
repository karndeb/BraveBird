import os
import logging
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SETUP] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Root directory of the project (relative to this script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEIGHTS_DIR = PROJECT_ROOT / "data" / "weights"

# Model IDs
OMNIPARSER_REPO = "microsoft/OmniParser-v2.0"
QWEN_REPO = "Qwen/Qwen2.5-VL-7B-Instruct"
WHISPER_REPO = "Systran/faster-whisper-medium.en" # Optimized for faster-whisper

def ensure_dir(path: Path):
    """Creates directory if it doesn't exist."""
    if not path.exists():
        logger.info(f"📁 Creating directory: {path}")
        path.mkdir(parents=True, exist_ok=True)

def install_omniparser():
    """
    Downloads OmniParser V2 weights.
    Requires specific folder structure:
    - weights/omniparser/icon_detect/model.pt
    - weights/omniparser/icon_caption_florence/...
    """
    logger.info("⬇️  Downloading OmniParser V2 weights...")
    base_dir = WEIGHTS_DIR / "omniparser"
    ensure_dir(base_dir)

    # 1. Download YOLO Icon Detector
    detect_dir = base_dir / "icon_detect"
    ensure_dir(detect_dir)
    
    if not (detect_dir / "model.pt").exists():
        logger.info("   Downloading YOLOv10 weights...")
        hf_hub_download(
            repo_id=OMNIPARSER_REPO,
            filename="icon_detect/model.pt",
            local_dir=base_dir,
            local_dir_use_symlinks=False
        )
    else:
        logger.info("   YOLO weights already exist.")

    # 2. Download Florence-2 Captioner
    caption_dir = base_dir / "icon_caption_florence"
    ensure_dir(caption_dir)
    
    logger.info("   Downloading Florence-2 weights...")
    snapshot_download(
        repo_id=OMNIPARSER_REPO,
        allow_patterns=["icon_caption_florence/*"],
        local_dir=base_dir,
        local_dir_use_symlinks=False
    )
    logger.info("✅ OmniParser installed.")

def install_ui_ins():
    """
    Downloads Qwen2.5-VL-7B-Instruct for UI-Ins.
    """
    logger.info(f"⬇️  Downloading UI-Ins Backbone ({QWEN_REPO})...")
    target_dir = WEIGHTS_DIR / "ui-ins" / "Qwen" / "Qwen2.5-VL-7B-Instruct"
    ensure_dir(target_dir)

    # We download to a specific structure because vLLM inside Docker 
    # expects a clean model folder.
    snapshot_download(
        repo_id=QWEN_REPO,
        local_dir=target_dir,
        local_dir_use_symlinks=False,
        # Exclude flax/tf weights to save space
        ignore_patterns=["*.msgpack", "*.h5", "*.ot"] 
    )
    logger.info("✅ UI-Ins (Qwen2.5-VL) installed.")

def install_whisper():
    """
    Downloads Faster-Whisper (CTranslate2) weights.
    """
    logger.info(f"⬇️  Downloading Whisper ({WHISPER_REPO})...")
    target_dir = WEIGHTS_DIR / "whisper"
    ensure_dir(target_dir)

    snapshot_download(
        repo_id=WHISPER_REPO,
        local_dir=target_dir,
        local_dir_use_symlinks=False
    )
    logger.info("✅ Whisper installed.")

def main():
    logger.info(f"🚀 Starting Model Setup. Target: {WEIGHTS_DIR}")
    
    try:
        install_omniparser()
        install_ui_ins()
        install_whisper()
        
        logger.info("🎉 All models downloaded successfully!")
        logger.info("   You can now run 'docker-compose up -d'")
        
    except Exception as e:
        logger.critical(f"🔥 Setup failed: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
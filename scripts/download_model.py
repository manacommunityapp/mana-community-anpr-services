"""
scripts/download_model.py — Download pretrained YOLOv11 license plate detection weights.

Uses the Hugging Face Hub to download 'morsetechlab/yolov11-license-plate-detection'.
Falls back to standard YOLOv8n if HF download fails.

Usage:
    python scripts/download_model.py
"""
import os
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

MODEL_FILENAME = "yolov8_plate.pt"
HF_REPO = "morsetechlab/yolov11-license-plate-detection"
HF_FILENAME = "best.pt"


def download_from_huggingface():
    try:
        from huggingface_hub import hf_hub_download
        print(f"Downloading from Hugging Face: {HF_REPO}/{HF_FILENAME}")
        path = hf_hub_download(
            repo_id=HF_REPO,
            filename=HF_FILENAME,
            local_dir=str(MODELS_DIR),
        )
        dest = MODELS_DIR / MODEL_FILENAME
        os.rename(path, dest)
        print(f"Model saved to: {dest}")
        return True
    except ImportError:
        print("huggingface_hub not installed. Run: pip install huggingface_hub")
    except Exception as e:
        print(f"HuggingFace download failed: {e}")
    return False


def download_yolov8_fallback():
    """Download standard YOLOv8n as fallback (not plate-specific)."""
    try:
        from ultralytics import YOLO
        print("Downloading YOLOv8n (fallback — not plate-specific)...")
        model = YOLO("yolov8n.pt")
        dest = MODELS_DIR / MODEL_FILENAME
        model.save(str(dest))
        print(f"Fallback model saved to: {dest}")
        return True
    except Exception as e:
        print(f"Fallback download failed: {e}")
    return False


if __name__ == "__main__":
    dest = MODELS_DIR / MODEL_FILENAME
    if dest.exists():
        print(f"Model already exists at {dest}. Delete it to re-download.")
        sys.exit(0)

    print("=== Mana ANPR Model Downloader ===")
    success = download_from_huggingface() or download_yolov8_fallback()
    if success:
        print("Done! Model ready for inference.")
    else:
        print("ERROR: Could not download model. Place a YOLOv8/v11 .pt file at models/yolov8_plate.pt manually.")
        sys.exit(1)

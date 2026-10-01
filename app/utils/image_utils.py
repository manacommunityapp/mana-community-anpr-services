"""
app/utils/image_utils.py — Image preprocessing helpers for better OCR accuracy.
"""
import io
import base64
from typing import Tuple

import cv2
import numpy as np
from PIL import Image


def load_image_bytes(data: bytes) -> np.ndarray:
    """Load image bytes into an OpenCV numpy array (BGR)."""
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes — unsupported format or corrupted data.")
    return img


def load_image_base64(b64_string: str) -> np.ndarray:
    """Decode a base64-encoded image string into an OpenCV array."""
    # Strip data URI prefix if present (data:image/jpeg;base64,...)
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    raw = base64.b64decode(b64_string)
    return load_image_bytes(raw)


def preprocess_for_ocr(crop: np.ndarray) -> np.ndarray:
    """
    Preprocess a cropped plate region for better OCR accuracy.
    Steps:
    1. Upscale if small (min 80px height for EasyOCR)
    2. Convert to grayscale
    3. Apply CLAHE contrast enhancement
    4. Bilateral filter to denoise while preserving edges
    5. Adaptive threshold for binary image
    """
    h, w = crop.shape[:2]

    # 1. Upscale to at least 80px height
    if h < 80:
        scale = 80.0 / h
        crop = cv2.resize(crop, (int(w * scale), 80), interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # 3. CLAHE contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    # 4. Bilateral denoise
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

    # 5. Adaptive threshold
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Return 3-channel image (EasyOCR expects BGR or RGB)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def crop_region(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Crop a bounding box (x1, y1, x2, y2) from the image."""
    x1, y1, x2, y2 = bbox
    # Add small padding
    pad = 4
    h, w = image.shape[:2]
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)
    return image[y1:y2, x1:x2]


def numpy_to_pil(image: np.ndarray) -> Image.Image:
    """Convert OpenCV BGR image to PIL RGB image."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

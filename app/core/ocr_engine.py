"""
app/core/ocr_engine.py — EasyOCR-based text extraction from cropped plate images.

EasyOCR is preferred over Tesseract for Indian plates because:
- Handles varied fonts including Indian number plate fonts
- No tessdata language pack installation needed
- Better accuracy on low-resolution / blurry plates
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class OcrResult:
    text: str
    confidence: float
    bbox: Optional[List] = None


class OcrEngine:
    """EasyOCR-powered text extraction engine."""

    def __init__(self, languages: List[str], gpu: bool = False):
        self.languages = languages
        self.gpu = gpu
        self._reader = None
        self._load_reader()

    def _load_reader(self) -> None:
        try:
            import easyocr
            log.info("Initialising EasyOCR reader", languages=self.languages, gpu=self.gpu)
            # EasyOCR reader initialisation is expensive — done once at startup
            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=False,
                # Optimise for single-line horizontal plate text
                paragraph=False,
            )
            log.info("EasyOCR reader ready")
        except ImportError:
            log.error("easyocr not installed. Run: pip install easyocr")
            raise

    def extract_text(self, image: np.ndarray) -> List[OcrResult]:
        """
        Extract all text from the image and return results sorted by confidence.

        Args:
            image: OpenCV BGR numpy array (cropped plate region, preprocessed)

        Returns:
            List of OcrResult ordered by confidence descending.
        """
        if self._reader is None:
            raise RuntimeError("OCR reader not initialised")

        raw = self._reader.readtext(image, detail=1, allowlist=self._allowlist())

        results: List[OcrResult] = []
        for (bbox, text, conf) in raw:
            cleaned = self._clean(text)
            if cleaned:
                results.append(OcrResult(text=cleaned, confidence=conf, bbox=bbox))

        return sorted(results, key=lambda r: r.confidence, reverse=True)

    def extract_best(self, image: np.ndarray) -> Optional[OcrResult]:
        """Return the highest-confidence OCR result."""
        results = self.extract_text(image)
        return results[0] if results else None

    @staticmethod
    def _allowlist() -> str:
        """Character allowlist for Indian number plates."""
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

    @staticmethod
    def _clean(text: str) -> str:
        """Remove stray characters; keep alphanumeric and spaces."""
        import re
        return re.sub(r"[^A-Z0-9 ]", "", text.upper()).strip()

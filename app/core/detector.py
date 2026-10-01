"""
app/core/detector.py — YOLOv8 number plate bounding box detection.

On first run, if the custom model is not found, falls back to the
pretrained YOLOv8n model and uses the 'license plate' class (class 0 in
the LP detection dataset). Replace with a fine-tuned Indian plate model
for production accuracy.

Model download:
  python scripts/download_model.py
"""
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class DetectionResult:
    bbox: tuple          # (x1, y1, x2, y2) in pixel coords
    confidence: float
    class_name: str = "license_plate"


class PlateDetector:
    """YOLOv8-based license plate detector."""

    def __init__(self, model_path: str, min_confidence: float = 0.80):
        self.model_path = model_path
        self.min_confidence = min_confidence
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
            if os.path.exists(self.model_path):
                log.info("Loading custom YOLO model", path=self.model_path)
                self._model = YOLO(self.model_path)
            else:
                log.warning(
                    "Custom model not found, using pretrained YOLOv8n. "
                    "Run scripts/download_model.py for better accuracy.",
                    expected_path=self.model_path,
                )
                # Fallback: use a general YOLOv8n (not plate-specific)
                self._model = YOLO("yolov8n.pt")
        except ImportError:
            log.error("ultralytics not installed. Run: pip install ultralytics")
            raise

    def detect(self, image: np.ndarray) -> List[DetectionResult]:
        """
        Run YOLO inference on an image and return all detected plate bounding boxes
        above the confidence threshold.

        Args:
            image: OpenCV BGR numpy array

        Returns:
            List of DetectionResult sorted by confidence descending.
        """
        if self._model is None:
            raise RuntimeError("YOLO model not loaded")

        results = self._model(image, verbose=False)
        detections: List[DetectionResult] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < self.min_confidence:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(DetectionResult(
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                ))

        return sorted(detections, key=lambda d: d.confidence, reverse=True)

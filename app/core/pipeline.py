"""
app/core/pipeline.py — End-to-end ANPR recognition pipeline.

Orchestrates:
  1. Load image (bytes / base64 / numpy array)
  2. YOLOv11 plate detection
  3. Crop + preprocess each detected region
  4. EasyOCR / PaddleOCR text extraction
  5. Indian plate validation and normalisation
  6. Return final RecognitionResult
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import numpy as np

from app.core.detector import PlateDetector, DetectionResult
from app.core.ocr_engine import OcrEngine, OcrResult
from app.core.plate_validator import validate_plate, PlateValidationResult
from app.utils.image_utils import crop_region, preprocess_for_ocr
from app.utils.logger import get_logger

log = get_logger(__name__)


class RecognitionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INVALID_PLATE = "INVALID_PLATE"
    NO_PLATE_FOUND = "NO_PLATE_FOUND"


@dataclass
class PlateReading:
    """A single plate candidate found in the image."""
    raw_ocr_text: str
    normalised_plate: str
    detection_confidence: float
    ocr_confidence: float
    combined_confidence: float
    plate_format: Optional[str]
    state_code: Optional[str]
    is_valid_format: bool
    bbox: tuple  # (x1, y1, x2, y2)


@dataclass
class RecognitionResult:
    """Overall result for one image frame."""
    status: RecognitionStatus
    best_plate: Optional[str]               # normalised plate text of top candidate
    best_confidence: float
    all_readings: List[PlateReading] = field(default_factory=list)
    processing_ms: float = 0.0
    gate_id: Optional[str] = None


class AnprPipeline:
    """
    Stateless ANPR recognition pipeline.
    The detector and OCR reader are injected as singletons (loaded at startup).
    """

    def __init__(
        self,
        detector: PlateDetector,
        ocr_engine: OcrEngine,
        min_confidence: float = 0.80,
        min_ocr_confidence: float = 0.75,
    ):
        self._detector = detector
        self._ocr = ocr_engine
        self._min_conf = min_confidence
        self._min_ocr_conf = min_ocr_confidence

    def process(self, image: np.ndarray, gate_id: Optional[str] = None) -> RecognitionResult:
        """
        Synchronous pipeline run (called inside executor to avoid blocking event loop).

        Args:
            image: OpenCV BGR numpy array
            gate_id: Optional gate identifier (GATE_MAIN_IN, etc.)

        Returns:
            RecognitionResult with best plate candidate.
        """
        start = time.perf_counter()

        # ── Step 1: Detect plate bounding boxes ──────────────────────────────
        detections: List[DetectionResult] = self._detector.detect(image)
        if not detections:
            return RecognitionResult(
                status=RecognitionStatus.NO_PLATE_FOUND,
                best_plate=None,
                best_confidence=0.0,
                processing_ms=(time.perf_counter() - start) * 1000,
                gate_id=gate_id,
            )

        readings: List[PlateReading] = []

        # ── Step 2: OCR each detected region ─────────────────────────────────
        for det in detections:
            crop = crop_region(image, det.bbox)
            preprocessed = preprocess_for_ocr(crop)

            ocr_result: Optional[OcrResult] = self._ocr.extract_best(preprocessed)
            if ocr_result is None or ocr_result.confidence < self._min_ocr_conf:
                continue

            # ── Step 3: Validate Indian plate format ─────────────────────────
            validation: PlateValidationResult = validate_plate(ocr_result.text)
            combined_conf = (
                det.confidence * 0.5 + ocr_result.confidence * 0.5
                - validation.confidence_penalty
            )

            readings.append(PlateReading(
                raw_ocr_text=ocr_result.text,
                normalised_plate=validation.normalised,
                detection_confidence=det.confidence,
                ocr_confidence=ocr_result.confidence,
                combined_confidence=round(combined_conf, 4),
                plate_format=validation.plate_format,
                state_code=validation.state_code,
                is_valid_format=validation.is_valid,
                bbox=det.bbox,
            ))

        if not readings:
            return RecognitionResult(
                status=RecognitionStatus.NO_PLATE_FOUND,
                best_plate=None,
                best_confidence=0.0,
                processing_ms=(time.perf_counter() - start) * 1000,
                gate_id=gate_id,
            )

        # ── Step 4: Pick best candidate ───────────────────────────────────────
        best = max(readings, key=lambda r: r.combined_confidence)

        if not best.is_valid_format:
            status = RecognitionStatus.INVALID_PLATE
        elif best.combined_confidence < self._min_conf:
            status = RecognitionStatus.LOW_CONFIDENCE
        else:
            status = RecognitionStatus.SUCCESS

        ms = (time.perf_counter() - start) * 1000
        log.info(
            "Recognition complete",
            plate=best.normalised_plate,
            confidence=best.combined_confidence,
            status=status,
            gate_id=gate_id,
            processing_ms=round(ms, 1),
        )

        return RecognitionResult(
            status=status,
            best_plate=best.normalised_plate,
            best_confidence=best.combined_confidence,
            all_readings=readings,
            processing_ms=round(ms, 1),
            gate_id=gate_id,
        )

    async def process_async(self, image: np.ndarray, gate_id: Optional[str] = None) -> RecognitionResult:
        """
        Non-blocking async wrapper — runs inference in thread pool executor
        so the FastAPI event loop is never blocked.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process, image, gate_id)

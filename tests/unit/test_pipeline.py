"""
tests/unit/test_pipeline.py — Unit tests for the ANPR pipeline with mocked detector and OCR.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app.core.pipeline import AnprPipeline, RecognitionStatus
from app.core.detector import DetectionResult
from app.core.ocr_engine import OcrResult


def make_pipeline(detection=None, ocr_text=None, ocr_conf=0.95):
    """Build a pipeline with mocked detector and OCR engine."""
    mock_detector = MagicMock()
    mock_ocr = MagicMock()

    if detection is not None:
        mock_detector.detect.return_value = [detection]
    else:
        mock_detector.detect.return_value = []

    if ocr_text is not None:
        mock_ocr.extract_best.return_value = OcrResult(text=ocr_text, confidence=ocr_conf)
    else:
        mock_ocr.extract_best.return_value = None

    return AnprPipeline(
        detector=mock_detector,
        ocr_engine=mock_ocr,
        min_confidence=0.80,
        min_ocr_confidence=0.75,
    )


class TestAnprPipeline:

    def _blank_image(self) -> np.ndarray:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def test_no_plate_found_when_no_detections(self):
        pipeline = make_pipeline(detection=None)
        result = pipeline.process(self._blank_image())
        assert result.status == RecognitionStatus.NO_PLATE_FOUND
        assert result.best_plate is None

    def test_success_with_valid_plate(self):
        det = DetectionResult(bbox=(10, 10, 200, 60), confidence=0.95)
        pipeline = make_pipeline(detection=det, ocr_text="MH12AB1234", ocr_conf=0.92)
        result = pipeline.process(self._blank_image())
        assert result.status == RecognitionStatus.SUCCESS
        assert result.best_plate == "MH12AB1234"

    def test_invalid_plate_format_flagged(self):
        det = DetectionResult(bbox=(10, 10, 200, 60), confidence=0.90)
        pipeline = make_pipeline(detection=det, ocr_text="XXXXXXXX", ocr_conf=0.91)
        result = pipeline.process(self._blank_image())
        assert result.status == RecognitionStatus.INVALID_PLATE

    def test_low_confidence_detection(self):
        det = DetectionResult(bbox=(10, 10, 200, 60), confidence=0.85)
        # OCR confidence below min_ocr_confidence
        pipeline = make_pipeline(detection=det, ocr_text="MH12AB1234", ocr_conf=0.60)
        result = pipeline.process(self._blank_image())
        # Low OCR confidence -> no readings qualify
        assert result.status in (RecognitionStatus.NO_PLATE_FOUND, RecognitionStatus.LOW_CONFIDENCE)

    def test_gate_id_propagated(self):
        det = DetectionResult(bbox=(10, 10, 200, 60), confidence=0.95)
        pipeline = make_pipeline(detection=det, ocr_text="KA01MN5678", ocr_conf=0.90)
        result = pipeline.process(self._blank_image(), gate_id="GATE_MAIN_IN")
        assert result.gate_id == "GATE_MAIN_IN"

    def test_bh_series_plate_recognised(self):
        det = DetectionResult(bbox=(10, 10, 200, 60), confidence=0.93)
        pipeline = make_pipeline(detection=det, ocr_text="24BH1234A", ocr_conf=0.91)
        result = pipeline.process(self._blank_image())
        assert result.status == RecognitionStatus.SUCCESS
        assert "BH" in result.best_plate

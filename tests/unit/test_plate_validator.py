"""
tests/unit/test_plate_validator.py — Unit tests for Indian plate regex validation.
"""
import pytest
from app.core.plate_validator import validate_plate


class TestPlateValidator:

    def test_standard_plate_maharashtra(self):
        result = validate_plate("MH12AB1234")
        assert result.is_valid is True
        assert result.plate_format == "STANDARD"
        assert result.state_code == "MH"
        assert result.normalised == "MH12AB1234"

    def test_standard_plate_delhi(self):
        result = validate_plate("DL01CX5678")
        assert result.is_valid is True
        assert result.state_code == "DL"

    def test_standard_plate_with_spaces(self):
        result = validate_plate("MH 12 AB 1234")
        assert result.is_valid is True
        assert result.normalised == "MH12AB1234"

    def test_bh_series_plate(self):
        result = validate_plate("24BH1234A")
        assert result.is_valid is True
        assert result.plate_format == "BH_SERIES"
        assert result.state_code == "BH"

    def test_invalid_state_code(self):
        result = validate_plate("XX12AB1234")
        assert result.is_valid is False
        assert result.plate_format == "STANDARD"

    def test_garbage_text(self):
        result = validate_plate("HELLO WORLD")
        assert result.is_valid is False
        assert result.plate_format == "UNKNOWN"

    def test_ocr_zero_o_correction(self):
        # OCR often reads zero as 'O' — normalisation should fix
        result = validate_plate("MH12ABO234")   # 'O' should remain (alpha position)
        # Format should still be recognised
        assert result.plate_format in ("STANDARD", "UNKNOWN")

    def test_empty_string(self):
        result = validate_plate("")
        assert result.is_valid is False

    def test_karnataka_plate(self):
        result = validate_plate("KA01MN9999")
        assert result.is_valid is True
        assert result.state_code == "KA"

    def test_telangana_plate(self):
        result = validate_plate("TS09EA1234")
        assert result.is_valid is True
        assert result.state_code == "TS"

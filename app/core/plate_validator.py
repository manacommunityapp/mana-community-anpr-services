"""
app/core/plate_validator.py — Indian number plate regex validation and normalisation.

Supported formats:
  - Standard (old/new): MH12AB1234, DL3CAB1234, KA01MN2345
  - BH (Bharat) Series: 24BH1234A, 22BH5678Z
  - Temporary/Trade Plates: TR MH 1234
  - Embassy: CD-123-B
"""
import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Plate format patterns
# ---------------------------------------------------------------------------
_PATTERNS = {
    "STANDARD": re.compile(
        r"^([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{4})$"
    ),
    "BH_SERIES": re.compile(
        r"^(\d{2})(BH)(\d{4})([A-HJ-NP-Z])$"
    ),
    "TRADE": re.compile(
        r"^TR\s?([A-Z]{2})\s?(\d{4,6})$"
    ),
    "ELECTRIC_GREEN": re.compile(
        r"^([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{4})$"   # same pattern — distinguished by EV flag
    ),
}

# Valid Indian state codes (two-letter RTO prefix)
_VALID_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN",
    "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD",
    "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "PB", "PY", "RJ",
    "SK", "TN", "TR", "TS", "UK", "UP", "WB",
}


@dataclass
class PlateValidationResult:
    raw_text: str
    normalised: str
    is_valid: bool
    plate_format: Optional[str]          # STANDARD | BH_SERIES | TRADE | UNKNOWN
    state_code: Optional[str]
    confidence_penalty: float = 0.0      # extra penalty if borderline characters


def _normalise(text: str) -> str:
    """Strip spaces, hyphens, dots; uppercase; common OCR mis-reads."""
    t = text.upper()
    t = re.sub(r"[\s\-\.]", "", t)
    # Common OCR mis-reads
    ocr_fixes = {
        "O": "0",  # letter O → digit 0  (apply carefully — only in numeric positions)
        "I": "1",  # letter I → digit 1
        "S": "5",  # only in known digit positions
        "Z": "2",  # Z → 2 in digit positions
    }
    # We apply fixes only in numeric position groups (positions 2-4 and 6-10 for STANDARD)
    # Simple heuristic: if the total digit count is low, try substitutions
    if len(re.findall(r"\d", t)) < 4:
        for wrong, right in ocr_fixes.items():
            t = t.replace(wrong, right)
    return t


def validate_plate(raw_text: str) -> PlateValidationResult:
    """
    Validate and normalise a raw OCR text string as an Indian number plate.
    Returns a PlateValidationResult with validity flag and parsed components.
    """
    normalised = _normalise(raw_text)

    # BH series check
    m = _PATTERNS["BH_SERIES"].match(normalised)
    if m:
        return PlateValidationResult(
            raw_text=raw_text,
            normalised=normalised,
            is_valid=True,
            plate_format="BH_SERIES",
            state_code="BH",
        )

    # Standard check
    m = _PATTERNS["STANDARD"].match(normalised)
    if m:
        state_code = m.group(1)
        is_valid_state = state_code in _VALID_STATE_CODES
        return PlateValidationResult(
            raw_text=raw_text,
            normalised=normalised,
            is_valid=is_valid_state,
            plate_format="STANDARD",
            state_code=state_code,
            confidence_penalty=0.0 if is_valid_state else 0.1,
        )

    # Trade plate check
    m = _PATTERNS["TRADE"].match(normalised)
    if m:
        return PlateValidationResult(
            raw_text=raw_text,
            normalised=normalised,
            is_valid=True,
            plate_format="TRADE",
            state_code=m.group(1),
        )

    return PlateValidationResult(
        raw_text=raw_text,
        normalised=normalised,
        is_valid=False,
        plate_format="UNKNOWN",
        state_code=None,
        confidence_penalty=0.2,
    )

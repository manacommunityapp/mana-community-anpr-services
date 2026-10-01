"""
app/models/schemas.py — Pydantic request/response schemas for ANPR API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class GateDirection(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    UNKNOWN = "UNKNOWN"


class BarrierAction(str, Enum):
    OPEN = "OPEN"      # Resident / authorised visitor
    HOLD = "HOLD"      # Unknown plate — alert security
    DENY = "DENY"      # Blacklisted vehicle


class RecognitionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INVALID_PLATE = "INVALID_PLATE"
    NO_PLATE_FOUND = "NO_PLATE_FOUND"


# ── Request schemas ────────────────────────────────────────────────────────

class Base64ImageRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image (JPEG/PNG/BMP)")
    gate_id: Optional[str] = Field(None, description="Gate identifier, e.g. GATE_MAIN_IN")
    direction: Optional[GateDirection] = Field(None)


class StreamStartRequest(BaseModel):
    gate_id: str = Field(..., description="Unique gate identifier")
    rtsp_url: str = Field(..., description="RTSP stream URL of the gate camera")
    direction: Optional[GateDirection] = Field(GateDirection.ENTRY)


class StreamStopRequest(BaseModel):
    gate_id: str


# ── Response schemas ───────────────────────────────────────────────────────

class PlateReadingResponse(BaseModel):
    raw_ocr_text: str
    normalised_plate: str
    detection_confidence: float
    ocr_confidence: float
    combined_confidence: float
    plate_format: Optional[str]
    state_code: Optional[str]
    is_valid_format: bool


class RecognitionResponse(BaseModel):
    status: RecognitionStatus
    best_plate: Optional[str]
    best_confidence: float
    all_readings: List[PlateReadingResponse] = []
    processing_ms: float
    gate_id: Optional[str]
    recognised_at: datetime = Field(default_factory=datetime.utcnow)


class GateEventResponse(BaseModel):
    event_id: int
    gate_id: str
    direction: GateDirection
    plate_number: Optional[str]
    confidence: float
    status: RecognitionStatus
    barrier_action: BarrierAction
    webhook_sent: bool
    created_at: datetime


class GateStatusResponse(BaseModel):
    gate_id: str
    rtsp_url: str
    is_streaming: bool
    direction: GateDirection
    last_event_at: Optional[datetime]
    frames_processed: int


class WebhookPayload(BaseModel):
    """Payload sent to mana-community-service /api/parking/anpr/webhook"""
    event_id: int
    gate_id: str
    direction: GateDirection
    plate_number: str
    confidence: float
    status: str
    recognised_at: str
    source_service: str = "mana-anpr-service"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    models_loaded: bool
    active_streams: int

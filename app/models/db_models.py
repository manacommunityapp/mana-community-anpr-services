"""
app/models/db_models.py — SQLAlchemy models for local ANPR event audit log.
"""
from datetime import datetime

from sqlalchemy import Column, Float, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AnprGateEvent(Base):
    """
    Audit trail for every plate recognition event at every gate.
    Written regardless of whether the plate is recognised or not.
    """
    __tablename__ = "anpr_gate_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gate_id = Column(String(50), nullable=False, index=True)
    direction = Column(String(10), nullable=False, default="UNKNOWN")   # ENTRY / EXIT
    plate_number = Column(String(20), nullable=True, index=True)         # normalised plate
    raw_ocr_text = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), nullable=False)                          # RecognitionStatus
    plate_format = Column(String(20), nullable=True)                     # STANDARD / BH_SERIES
    barrier_action = Column(String(10), nullable=False, default="HOLD")  # OPEN / HOLD / DENY
    webhook_sent = Column(Boolean, nullable=False, default=False)
    webhook_response_code = Column(Integer, nullable=True)
    processing_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    raw_image_path = Column(Text, nullable=True)   # optional saved frame path

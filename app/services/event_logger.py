"""
app/services/event_logger.py — Local SQLite/PostgreSQL ANPR event audit log.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.db_models import AnprGateEvent, Base
from app.models.schemas import GateDirection, RecognitionStatus
from app.utils.logger import get_logger

log = get_logger(__name__)


class EventLogger:
    def __init__(self, db_url: str):
        self._engine = create_async_engine(db_url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def init_db(self) -> None:
        """Create tables on startup."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database tables initialised")

    async def log_event(
        self,
        gate_id: str,
        direction: str,
        plate_number: Optional[str],
        raw_ocr_text: Optional[str],
        confidence: float,
        status: str,
        plate_format: Optional[str],
        barrier_action: str,
        webhook_sent: bool,
        webhook_response_code: Optional[int],
        processing_ms: float,
    ) -> int:
        """Persist an ANPR gate event and return its generated ID."""
        event = AnprGateEvent(
            gate_id=gate_id,
            direction=direction,
            plate_number=plate_number,
            raw_ocr_text=raw_ocr_text,
            confidence=confidence,
            status=status,
            plate_format=plate_format,
            barrier_action=barrier_action,
            webhook_sent=webhook_sent,
            webhook_response_code=webhook_response_code,
            processing_ms=processing_ms,
            created_at=datetime.utcnow(),
        )
        async with self._session_factory() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event.id

    async def get_recent_events(self, gate_id: Optional[str] = None, limit: int = 50) -> List[AnprGateEvent]:
        async with self._session_factory() as session:
            query = select(AnprGateEvent).order_by(AnprGateEvent.created_at.desc()).limit(limit)
            if gate_id:
                query = query.where(AnprGateEvent.gate_id == gate_id)
            result = await session.execute(query)
            return result.scalars().all()

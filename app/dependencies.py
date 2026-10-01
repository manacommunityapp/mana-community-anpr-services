"""
app/dependencies.py — FastAPI dependency injection: models, services, settings.

All heavy objects (YOLO, OCR reader) are created once at app startup
using the FastAPI lifespan context and stored in app.state.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.core.detector import PlateDetector
from app.core.ocr_engine import OcrEngine
from app.core.pipeline import AnprPipeline
from app.services.event_logger import EventLogger
from app.services.stream_manager import StreamManager
from app.services.webhook_client import WebhookClient


def get_pipeline(request: Request) -> AnprPipeline:
    return request.app.state.pipeline


def get_event_logger(request: Request) -> EventLogger:
    return request.app.state.event_logger


def get_webhook_client(request: Request) -> WebhookClient:
    return request.app.state.webhook_client


def get_stream_manager(request: Request) -> StreamManager:
    return request.app.state.stream_manager


# Annotated type aliases for clean route signatures
PipelineDep = Annotated[AnprPipeline, Depends(get_pipeline)]
EventLoggerDep = Annotated[EventLogger, Depends(get_event_logger)]
WebhookDep = Annotated[WebhookClient, Depends(get_webhook_client)]
StreamManagerDep = Annotated[StreamManager, Depends(get_stream_manager)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

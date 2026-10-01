"""
app/api/routes/recognize.py — /api/v1/anpr/recognize endpoints.

Accepts either:
  - Multipart file upload (image file)
  - JSON body with base64-encoded image
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, status

from app.core.pipeline import RecognitionStatus
from app.dependencies import PipelineDep, EventLoggerDep, WebhookDep
from app.models.schemas import (
    RecognitionResponse, Base64ImageRequest, GateDirection, PlateReadingResponse
)
from app.utils.image_utils import load_image_bytes, load_image_base64
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/anpr", tags=["ANPR Recognition"])


async def _process_and_log(
    image_data: bytes,
    pipeline: PipelineDep,
    event_logger: EventLoggerDep,
    webhook_client: WebhookDep,
    gate_id: str | None,
    direction: GateDirection,
    background_tasks: BackgroundTasks,
) -> RecognitionResponse:
    """Shared logic for all recognition endpoints."""
    try:
        image = load_image_bytes(image_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    result = await pipeline.process_async(image, gate_id=gate_id)

    response = RecognitionResponse(
        status=result.status,
        best_plate=result.best_plate,
        best_confidence=result.best_confidence,
        all_readings=[
            PlateReadingResponse(**{
                k: v for k, v in vars(r).items()
                if k in PlateReadingResponse.model_fields
            })
            for r in result.all_readings
        ],
        processing_ms=result.processing_ms,
        gate_id=gate_id,
        recognised_at=datetime.now(timezone.utc),
    )

    # Persist event + push webhook asynchronously (non-blocking)
    background_tasks.add_task(
        _persist_and_notify, response, event_logger, webhook_client, direction
    )

    return response


async def _persist_and_notify(
    response: RecognitionResponse,
    event_logger: EventLoggerDep,
    webhook_client: WebhookDep,
    direction: GateDirection,
) -> None:
    """Background task: save event + send webhook."""
    # Determine barrier action
    barrier_action = "OPEN" if response.status == RecognitionStatus.SUCCESS else "HOLD"

    event_id = await event_logger.log_event(
        gate_id=response.gate_id or "UNKNOWN",
        direction=direction.value,
        plate_number=response.best_plate,
        raw_ocr_text=response.all_readings[0].raw_ocr_text if response.all_readings else None,
        confidence=response.best_confidence,
        status=response.status.value,
        plate_format=response.all_readings[0].plate_format if response.all_readings else None,
        barrier_action=barrier_action,
        webhook_sent=False,
        webhook_response_code=None,
        processing_ms=response.processing_ms,
    )

    if response.best_plate and response.status == RecognitionStatus.SUCCESS:
        success, code = await webhook_client.send_event(event_id, response, direction)
        # Update webhook sent status (fire and forget, no await)


@router.post("/recognize", response_model=RecognitionResponse, summary="Recognise plate from image file")
async def recognize_from_file(
    background_tasks: BackgroundTasks,
    pipeline: PipelineDep,
    event_logger: EventLoggerDep,
    webhook: WebhookDep,
    file: UploadFile = File(..., description="Image file (JPEG/PNG/BMP)"),
    gate_id: str | None = None,
    direction: GateDirection = GateDirection.ENTRY,
):
    """
    Upload a raw image frame from a gate camera for plate recognition.
    Processes synchronously and returns the result immediately.
    Webhook to mana-community-service fires in the background.
    """
    image_bytes = await file.read()
    return await _process_and_log(
        image_bytes, pipeline, event_logger, webhook, gate_id, direction, background_tasks
    )


@router.post("/recognize/base64", response_model=RecognitionResponse, summary="Recognise plate from base64 image")
async def recognize_from_base64(
    background_tasks: BackgroundTasks,
    pipeline: PipelineDep,
    event_logger: EventLoggerDep,
    webhook: WebhookDep,
    body: Base64ImageRequest,
):
    """
    Submit a base64-encoded image (from embedded systems / IoT devices that
    can't do multipart uploads).
    """
    try:
        image = load_image_base64(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid base64 image: {e}")

    import numpy as np, cv2
    _, buf = cv2.imencode(".jpg", image)
    image_bytes = buf.tobytes()

    return await _process_and_log(
        image_bytes, pipeline, event_logger, webhook,
        body.gate_id, body.direction or GateDirection.ENTRY, background_tasks
    )

"""
app/main.py — FastAPI application entry point.

Startup sequence:
  1. Configure structured logging
  2. Load YOLOv11 + EasyOCR models into app.state (done once)
  3. Initialise database tables
  4. Auto-start configured RTSP gate streams
  5. Register routers

Shutdown sequence:
  1. Stop all RTSP stream threads
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.middleware import register_middleware
from app.api.routes import recognize, stream, gates
from app.config import get_settings
from app.core.detector import PlateDetector
from app.core.ocr_engine import OcrEngine
from app.core.pipeline import AnprPipeline
from app.models.schemas import HealthResponse
from app.services.event_logger import EventLogger
from app.services.stream_manager import StreamManager
from app.services.webhook_client import WebhookClient
from app.utils.logger import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Replaces deprecated @app.on_event('startup') / 'shutdown'.
    """
    settings = get_settings()
    configure_logging(debug=(settings.app_env == "development"))

    log.info("Starting Mana ANPR Service", version=settings.app_version, env=settings.app_env)

    # ── Load ML models (heavy — done once) ───────────────────────────────────
    log.info("Loading YOLOv11 plate detector...")
    detector = PlateDetector(
        model_path=settings.yolo_model_path,
        min_confidence=settings.min_confidence,
    )

    log.info("Loading EasyOCR engine...", languages=settings.ocr_languages_list, gpu=settings.ocr_gpu)
    ocr = OcrEngine(languages=settings.ocr_languages_list, gpu=settings.ocr_gpu)

    pipeline = AnprPipeline(
        detector=detector,
        ocr_engine=ocr,
        min_confidence=settings.min_confidence,
        min_ocr_confidence=settings.min_ocr_confidence,
    )

    # ── Init database ─────────────────────────────────────────────────────────
    event_logger = EventLogger(db_url=settings.db_url)
    await event_logger.init_db()

    # ── Webhook client ────────────────────────────────────────────────────────
    webhook_client = WebhookClient(settings=settings)

    # ── Stream manager ────────────────────────────────────────────────────────
    def on_frame(frame, gate_id: str, direction: str):
        """Called from RTSP thread — schedules async pipeline processing."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    _process_frame(pipeline, event_logger, webhook_client, frame, gate_id, direction),
                    loop,
                )
        except Exception as e:
            log.error("Frame callback error", error=str(e), gate_id=gate_id)

    stream_manager = StreamManager(on_frame_callback=on_frame, sample_fps=settings.stream_sample_fps)

    # Store in app.state for dependency injection
    app.state.pipeline = pipeline
    app.state.event_logger = event_logger
    app.state.webhook_client = webhook_client
    app.state.stream_manager = stream_manager
    app.state.models_loaded = True

    # ── Auto-start configured gate streams ────────────────────────────────────
    for gate_id, rtsp_url in settings.gate_cameras.items():
        log.info("Auto-starting configured gate stream", gate_id=gate_id)
        stream_manager.start_stream(gate_id, rtsp_url)

    log.info("Mana ANPR Service ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("Shutting down ANPR Service — stopping streams...")
    stream_manager.stop_all()
    log.info("Shutdown complete")


async def _process_frame(pipeline, event_logger, webhook_client, frame, gate_id, direction):
    """Async coroutine: process a sampled frame from the RTSP stream."""
    from datetime import datetime, timezone
    from app.core.pipeline import RecognitionStatus
    from app.models.schemas import GateDirection, RecognitionResponse, PlateReadingResponse

    result = await pipeline.process_async(frame, gate_id=gate_id)

    if result.status == RecognitionStatus.NO_PLATE_FOUND:
        return   # No plate detected — skip logging noise

    barrier_action = "OPEN" if result.status == RecognitionStatus.SUCCESS else "HOLD"

    event_id = await event_logger.log_event(
        gate_id=gate_id,
        direction=direction,
        plate_number=result.best_plate,
        raw_ocr_text=result.all_readings[0].raw_ocr_text if result.all_readings else None,
        confidence=result.best_confidence,
        status=result.status.value,
        plate_format=result.all_readings[0].plate_format if result.all_readings else None,
        barrier_action=barrier_action,
        webhook_sent=False,
        webhook_response_code=None,
        processing_ms=result.processing_ms,
    )

    if result.best_plate and result.status == RecognitionStatus.SUCCESS:
        response = RecognitionResponse(
            status=result.status,
            best_plate=result.best_plate,
            best_confidence=result.best_confidence,
            all_readings=[
                PlateReadingResponse(**{k: v for k, v in vars(r).items() if k in PlateReadingResponse.model_fields})
                for r in result.all_readings
            ],
            processing_ms=result.processing_ms,
            gate_id=gate_id,
            recognised_at=datetime.now(timezone.utc),
        )
        dir_enum = GateDirection.ENTRY if direction == "ENTRY" else GateDirection.EXIT
        await webhook_client.send_event(event_id, response, dir_enum)


# ── Create app ────────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Mana Community ANPR Service",
    description=(
        "Automatic Number Plate Recognition microservice for the Mana Community platform. "
        "Processes gate camera frames using YOLOv11 + EasyOCR and pushes plate events "
        "to the mana-community-service backend webhook."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

register_middleware(app, settings.allowed_origins_list)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(recognize.router)
app.include_router(stream.router)
app.include_router(gates.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        models_loaded=getattr(app.state, "models_loaded", False),
        active_streams=app.state.stream_manager.active_count()
        if hasattr(app.state, "stream_manager") else 0,
    )


@app.get("/", tags=["Health"])
async def root():
    return {"service": "mana-community-anpr-service", "docs": "/docs", "health": "/health"}

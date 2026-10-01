"""
app/api/routes/gates.py — Gate configuration and event history endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Query

from app.dependencies import EventLoggerDep, StreamManagerDep, SettingsDep
from app.models.schemas import GateEventResponse, GateStatusResponse, GateDirection

router = APIRouter(prefix="/api/v1/anpr/gates", tags=["Gate Management"])


@router.get("", summary="List all configured gate cameras and stream status")
async def list_gates(manager: StreamManagerDep, settings: SettingsDep):
    """Returns all gates from config + their live stream status."""
    configured = settings.gate_cameras
    stream_states = manager.get_status()

    gates = []
    for gate_id, rtsp_url in configured.items():
        state = stream_states.get(gate_id)
        gates.append({
            "gate_id": gate_id,
            "rtsp_url": rtsp_url,
            "is_streaming": state.is_running if state else False,
            "frames_processed": state.frames_processed if state else 0,
            "last_event_at": state.last_event_at if state else None,
        })
    return {"gates": gates, "total": len(gates)}


@router.get("/{gate_id}/events", summary="Get recent ANPR events for a gate")
async def get_gate_events(
    gate_id: str,
    event_logger: EventLoggerDep,
    limit: int = Query(default=50, le=200),
):
    """Returns the most recent plate recognition events for the given gate."""
    events = await event_logger.get_recent_events(gate_id=gate_id, limit=limit)
    return {
        "gate_id": gate_id,
        "events": [
            {
                "id": e.id,
                "gate_id": e.gate_id,
                "direction": e.direction,
                "plate_number": e.plate_number,
                "confidence": e.confidence,
                "status": e.status,
                "barrier_action": e.barrier_action,
                "webhook_sent": e.webhook_sent,
                "processing_ms": e.processing_ms,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "count": len(events),
    }


@router.get("/events/all", summary="Get all recent events across all gates")
async def get_all_events(
    event_logger: EventLoggerDep,
    limit: int = Query(default=100, le=500),
):
    events = await event_logger.get_recent_events(gate_id=None, limit=limit)
    return {
        "events": [
            {
                "id": e.id,
                "gate_id": e.gate_id,
                "direction": e.direction,
                "plate_number": e.plate_number,
                "confidence": e.confidence,
                "status": e.status,
                "barrier_action": e.barrier_action,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "count": len(events),
    }

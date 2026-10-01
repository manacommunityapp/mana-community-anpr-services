"""
app/api/routes/stream.py — RTSP stream start/stop management endpoints.
"""
from fastapi import APIRouter, HTTPException, status

from app.dependencies import StreamManagerDep
from app.models.schemas import StreamStartRequest, StreamStopRequest, GateStatusResponse

router = APIRouter(prefix="/api/v1/anpr/stream", tags=["RTSP Stream Management"])


@router.post("/start", summary="Start RTSP stream processing for a gate")
async def start_stream(body: StreamStartRequest, manager: StreamManagerDep):
    """
    Start processing RTSP video stream from a gate camera.
    Each sampled frame will be run through the ANPR pipeline automatically.
    """
    started = manager.start_stream(body.gate_id, body.rtsp_url, body.direction.value if body.direction else "ENTRY")
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stream for gate '{body.gate_id}' is already running.",
        )
    return {"message": f"Stream started for gate '{body.gate_id}'", "gate_id": body.gate_id}


@router.post("/stop", summary="Stop RTSP stream processing")
async def stop_stream(body: StreamStopRequest, manager: StreamManagerDep):
    """Stop the background RTSP stream processing for a gate."""
    stopped = manager.stop_stream(body.gate_id)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active stream found for gate '{body.gate_id}'.",
        )
    return {"message": f"Stream stop signal sent for gate '{body.gate_id}'"}

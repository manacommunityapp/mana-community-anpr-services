"""
app/services/webhook_client.py — Push ANPR events to mana-community-service.

Sends a POST to MANA_BACKEND_WEBHOOK_URL with the recognised plate event.
The Java backend then validates the plate against registered residents
and commands the barrier open/hold.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import Settings
from app.models.schemas import RecognitionResponse, WebhookPayload, GateDirection, BarrierAction
from app.utils.logger import get_logger

log = get_logger(__name__)


class WebhookClient:
    def __init__(self, settings: Settings):
        self._url = settings.mana_backend_webhook_url
        self._api_key = settings.mana_backend_api_key
        self._timeout = settings.webhook_timeout_seconds

    async def send_event(
        self,
        event_id: int,
        result: RecognitionResponse,
        direction: GateDirection = GateDirection.UNKNOWN,
    ) -> tuple[bool, int]:
        """
        POST a recognition event to the Java backend webhook.

        Returns:
            (success: bool, http_status_code: int)
        """
        if not result.best_plate:
            return False, 0

        payload = WebhookPayload(
            event_id=event_id,
            gate_id=result.gate_id or "UNKNOWN",
            direction=direction,
            plate_number=result.best_plate,
            confidence=result.best_confidence,
            status=result.status.value,
            recognised_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    self._url,
                    json=payload.model_dump(),
                    headers={
                        "Content-Type": "application/json",
                        "X-ANPR-API-Key": self._api_key,
                    },
                )
                success = resp.status_code in (200, 201, 202)
                log.info(
                    "Webhook sent",
                    plate=result.best_plate,
                    gate=result.gate_id,
                    http_status=resp.status_code,
                    success=success,
                )
                return success, resp.status_code
        except httpx.TimeoutException:
            log.error("Webhook timed out", url=self._url, plate=result.best_plate)
            return False, 0
        except Exception as exc:
            log.error("Webhook failed", error=str(exc), plate=result.best_plate)
            return False, 0

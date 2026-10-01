"""
app/services/stream_manager.py — RTSP stream lifecycle manager.

Each gate camera runs as a background daemon thread.
The manager starts/stops streams and delegates each sampled frame
to the ANPR pipeline for processing.
"""
from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Optional

import cv2
import numpy as np

from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class StreamState:
    gate_id: str
    rtsp_url: str
    direction: str
    is_running: bool = False
    frames_processed: int = 0
    last_event_at: Optional[datetime] = None
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)


class StreamManager:
    """
    Manages multiple concurrent RTSP camera streams.
    Each stream runs in its own daemon thread with a ring-buffer (deque maxlen=1)
    so only the latest frame is processed — avoiding processing stale queued frames.
    """

    def __init__(
        self,
        on_frame_callback: Callable[[np.ndarray, str, str], None],
        sample_fps: int = 2,
    ):
        """
        Args:
            on_frame_callback: Called with (frame, gate_id, direction) for each sampled frame.
            sample_fps: How many frames per second to process per stream.
        """
        self._streams: Dict[str, StreamState] = {}
        self._callback = on_frame_callback
        self._frame_interval = 1.0 / max(1, sample_fps)

    def start_stream(self, gate_id: str, rtsp_url: str, direction: str = "ENTRY") -> bool:
        if gate_id in self._streams and self._streams[gate_id].is_running:
            log.warning("Stream already running", gate_id=gate_id)
            return False

        state = StreamState(gate_id=gate_id, rtsp_url=rtsp_url, direction=direction)
        state._stop_event = threading.Event()
        state.is_running = True
        state._thread = threading.Thread(
            target=self._capture_loop,
            args=(state,),
            daemon=True,
            name=f"anpr-stream-{gate_id}",
        )
        self._streams[gate_id] = state
        state._thread.start()
        log.info("RTSP stream started", gate_id=gate_id, url=rtsp_url)
        return True

    def stop_stream(self, gate_id: str) -> bool:
        state = self._streams.get(gate_id)
        if not state:
            return False
        state._stop_event.set()
        state.is_running = False
        log.info("RTSP stream stopping", gate_id=gate_id)
        return True

    def stop_all(self) -> None:
        for gate_id in list(self._streams.keys()):
            self.stop_stream(gate_id)

    def get_status(self) -> Dict[str, StreamState]:
        return dict(self._streams)

    def active_count(self) -> int:
        return sum(1 for s in self._streams.values() if s.is_running)

    def _capture_loop(self, state: StreamState) -> None:
        """
        Runs in a daemon thread.
        Reconnects automatically if the RTSP stream drops.
        Processes one frame every (1 / sample_fps) seconds.
        """
        frame_buffer: deque = deque(maxlen=1)

        while not state._stop_event.is_set():
            log.info("Connecting to RTSP stream", gate_id=state.gate_id)
            cap = cv2.VideoCapture(state.rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # Minimize buffering lag

            if not cap.isOpened():
                log.warning("Cannot open RTSP stream, retrying in 5s", gate_id=state.gate_id)
                time.sleep(5)
                continue

            last_process_time = 0.0

            while not state._stop_event.is_set() and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    log.warning("Frame read failed, reconnecting", gate_id=state.gate_id)
                    break

                frame_buffer.append(frame)

                now = time.monotonic()
                if now - last_process_time >= self._frame_interval:
                    last_process_time = now
                    if frame_buffer:
                        self._callback(frame_buffer[-1], state.gate_id, state.direction)
                        state.frames_processed += 1

            cap.release()
            if not state._stop_event.is_set():
                log.warning("Reconnecting in 3s", gate_id=state.gate_id)
                time.sleep(3)

        state.is_running = False
        log.info("RTSP stream stopped", gate_id=state.gate_id)

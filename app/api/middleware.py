"""
app/api/middleware.py — CORS + request logging middleware.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.utils.logger import get_logger

log = get_logger(__name__)


def register_middleware(app: FastAPI, allowed_origins: list) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        log.info(
            "Request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round(ms, 1),
        )
        return response

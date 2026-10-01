"""
app/config.py — Application settings via Pydantic BaseSettings.
All values are overridable via environment variables or .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Mana Community ANPR Service"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", env="APP_ENV")
    app_port: int = Field(default=8001, env="APP_PORT")
    debug: bool = Field(default=False)

    # Backend webhook
    mana_backend_webhook_url: str = Field(env="MANA_BACKEND_WEBHOOK_URL")
    mana_backend_api_key: str = Field(env="MANA_BACKEND_API_KEY")
    webhook_timeout_seconds: int = Field(default=5)

    # Model paths
    yolo_model_path: str = Field(default="models/yolov8_plate.pt", env="YOLO_MODEL_PATH")
    ocr_languages: str = Field(default="en", env="OCR_LANGUAGES")
    ocr_gpu: bool = Field(default=False, env="OCR_GPU")

    # Thresholds
    min_confidence: float = Field(default=0.80, env="MIN_CONFIDENCE")
    min_ocr_confidence: float = Field(default=0.75, env="MIN_OCR_CONFIDENCE")

    # RTSP stream settings
    stream_sample_fps: int = Field(default=2, env="STREAM_SAMPLE_FPS")

    # Gate cameras (map gateId -> RTSP URL via env vars)
    camera_gate_main_in: str = Field(default="", env="CAMERA_GATE_MAIN_IN")
    camera_gate_main_out: str = Field(default="", env="CAMERA_GATE_MAIN_OUT")
    camera_gate_basement: str = Field(default="", env="CAMERA_GATE_BASEMENT")

    # Database
    db_url: str = Field(
        default="sqlite+aiosqlite:///./anpr_events.db", env="DB_URL"
    )

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        env="ALLOWED_ORIGINS"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def ocr_languages_list(self) -> List[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",")]

    @property
    def gate_cameras(self) -> dict:
        """Return only configured gates (non-empty RTSP URLs)."""
        cameras = {}
        if self.camera_gate_main_in:
            cameras["GATE_MAIN_IN"] = self.camera_gate_main_in
        if self.camera_gate_main_out:
            cameras["GATE_MAIN_OUT"] = self.camera_gate_main_out
        if self.camera_gate_basement:
            cameras["GATE_BASEMENT"] = self.camera_gate_basement
        return cameras

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

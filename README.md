# mana-community-anpr-services

> **Mana Community — ANPR (Automatic Number Plate Recognition) Microservice**  
> Python · FastAPI · YOLOv8 · EasyOCR · OpenCV

A production-ready computer vision microservice that:
- Accepts raw image frames or RTSP stream snapshots from gate cameras
- Detects number plate bounding boxes using **YOLOv8**
- Extracts plate text using **EasyOCR** (supports Indian number plate formats)
- Validates the recognised plate against standard Indian plate regex patterns
- Pushes validated events to `mana-community-service` (Java Spring Boot) webhook
- Supports multi-gate configuration

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Indian Number Plate Formats Supported

| Format | Example |
|---|---|
| Standard | `MH12AB1234` |
| BH Series | `24BH1234A` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/anpr/recognize` | Submit image file for plate recognition |
| `POST` | `/api/v1/anpr/recognize/base64` | Submit base64 encoded image |
| `POST` | `/api/v1/anpr/stream/start` | Start RTSP stream processing |
| `POST` | `/api/v1/anpr/stream/stop` | Stop stream processing |
| `GET`  | `/api/v1/anpr/gates` | List configured gate cameras |
| `GET`  | `/api/v1/anpr/gates/{gateId}/events` | Recent events from a gate |
| `GET`  | `/health` | Health check |

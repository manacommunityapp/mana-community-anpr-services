# mana-community-anpr-services

> **Mana Community — ANPR (Automatic Number Plate Recognition) Microservice**
> Python · FastAPI · YOLOv11 · EasyOCR · PaddleOCR · OpenCV

A production-ready computer vision microservice that:
- Accepts raw image frames or RTSP stream snapshots from gate cameras
- Detects number plate bounding boxes using **YOLOv11** (ultralytics)
- Extracts plate text using **EasyOCR** (supports Indian number plate formats)
- Validates the recognised plate against standard Indian plate regex patterns
- Pushes validated events to `mana-community-service` (Java Spring Boot) webhook
- Supports multi-gate RTSP camera configuration with auto-reconnect

---

## Architecture

`
Camera (RTSP stream / HTTP image snapshot)
        |
        v
mana-community-anpr-services  (This service — Python/FastAPI)
 |-- Plate Detection   YOLOv11 bounding box
 |-- OCR Extraction    EasyOCR (Indian plate charset)
 |-- Plate Validation  Regex: STANDARD / BH_SERIES / TRADE
 -- Webhook Push      POST to mana-community-service
        |
        v
mana-community-service  (Java Spring Boot)
 |-- Plate lookup vs ResidentVehicle
 |-- Gate barrier OPEN / HOLD command
 -- AnprGateEvent audit log
`

---

## Getting Started

### Step 1 — Clone and create virtual environment

`ash
git clone https://github.com/manacommunityapp/mana-community-anpr-services.git
cd mana-community-anpr-services

# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python -m venv venv
source venv/bin/activate
`

### Step 2 — Install dependencies

`ash
pip install -r requirements.txt
`

> **Note:** Use `opencv-python-headless` (already in requirements.txt) for server/container deployments.
> Do NOT install both `opencv-python` and `opencv-python-headless` in the same environment.

### Step 3 — Download YOLOv11 plate detection model

`ash
pip install huggingface_hub
python scripts/download_model.py
`

This downloads the pretrained YOLOv11 license plate detection weights from
[morsetechlab/yolov11-license-plate-detection](https://huggingface.co/morsetechlab/yolov11-license-plate-detection)
into the `models/` directory.

> **Tip:** For production use on Indian gates, fine-tune the model on the
> [Indian Number Plate Kaggle dataset](https://www.kaggle.com/datasets/praveengovi/indian-number-plate-annotation)
> and replace `models/yolov8_plate.pt` with your custom weights.

### Step 4 — Configure environment

`ash
# Copy the example file
cp .env.example .env   # Linux/macOS
copy .env.example .env # Windows
`

Edit `.env` and set the required values:

`env
# Backend webhook (mana-community-service)
MANA_BACKEND_WEBHOOK_URL=http://localhost:8080/api/parking/anpr/webhook
MANA_BACKEND_API_KEY=your-shared-secret-here

# RTSP gate cameras
CAMERA_GATE_MAIN_IN=rtsp://admin:password@192.168.1.101:554/stream1
CAMERA_GATE_MAIN_OUT=rtsp://admin:password@192.168.1.102:554/stream1

# GPU inference (set true if NVIDIA GPU available)
OCR_GPU=false
`

### Step 5 — Test your RTSP camera connectivity (optional)

`ash
python scripts/test_camera.py rtsp://admin:password@192.168.1.101:554/stream1
`

### Step 6 — Run the service

`ash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
`

### Step 7 — Open Swagger UI and test

`
http://localhost:8001/docs
`

Use **POST /api/v1/anpr/recognize** to upload a test gate camera image and verify plate recognition.

---

## Running with Docker

### CPU (default)

`ash
docker-compose up --build
`

### GPU (NVIDIA CUDA)

`ash
docker build -f docker/Dockerfile.gpu -t mana-anpr-gpu .
docker run --gpus all -p 8001:8001 --env-file .env mana-anpr-gpu
`

---

## Indian Number Plate Formats Supported

| Format | Example | Pattern |
|---|---|---|
| Standard (state-RTO) | `MH12AB1234` | `[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}` |
| BH Series | `24BH1234A` | `\d{2}BH\d{4}[A-Z]` |
| Trade / Temporary | `TR MH 123456` | special handling |

Supported state codes: DL, MH, KA, TN, WB, RJ, UP, GJ, AP, TS, KL, HR, PB, MP, BR, OD, and all 37 Indian state/UT codes.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/anpr/recognize` | Upload image file for plate recognition |
| `POST` | `/api/v1/anpr/recognize/base64` | Submit base64-encoded image |
| `POST` | `/api/v1/anpr/stream/start` | Start RTSP stream processing for a gate |
| `POST` | `/api/v1/anpr/stream/stop` | Stop RTSP stream processing |
| `GET`  | `/api/v1/anpr/gates` | List all configured gate cameras |
| `GET`  | `/api/v1/anpr/gates/{gateId}/events` | Recent recognition events for a gate |
| `GET`  | `/api/v1/anpr/gates/events/all` | All recent events across all gates |
| `GET`  | `/health` | Health check (model loaded, active streams) |
| `GET`  | `/docs` | Swagger UI |

---

## Environment Variables Reference

| Variable | Description | Default |
|---|---|---|
| `APP_ENV` | `development` / `production` | `development` |
| `APP_PORT` | Service port | `8001` |
| `MANA_BACKEND_WEBHOOK_URL` | Java backend webhook URL | **required** |
| `MANA_BACKEND_API_KEY` | Shared secret for webhook auth | **required** |
| `YOLO_MODEL_PATH` | Path to YOLOv11 weights | `models/yolov8_plate.pt` |
| `OCR_LANGUAGES` | EasyOCR language codes | `en` |
| `OCR_GPU` | Use GPU for inference | `false` |
| `MIN_CONFIDENCE` | YOLO detection threshold | `0.80` |
| `MIN_OCR_CONFIDENCE` | OCR text confidence threshold | `0.75` |
| `STREAM_SAMPLE_FPS` | Frames per second to process per RTSP stream | `2` |
| `CAMERA_GATE_MAIN_IN` | RTSP URL — main entry gate | — |
| `CAMERA_GATE_MAIN_OUT` | RTSP URL — main exit gate | — |
| `CAMERA_GATE_BASEMENT` | RTSP URL — basement gate | — |
| `DB_URL` | Database connection (SQLite or PostgreSQL) | SQLite local file |

---

## Project Structure

`
mana-community-anpr-services/
|-- app/
|   |-- main.py                  FastAPI app + lifespan startup/shutdown
|   |-- config.py                Pydantic BaseSettings (env-driven config)
|   |-- dependencies.py          FastAPI DI: pipeline, event logger, webhook client
|   |-- core/
|   |   |-- detector.py          YOLOv11 plate bounding box detection
|   |   |-- ocr_engine.py        EasyOCR text extraction
|   |   |-- pipeline.py          End-to-end async recognition pipeline
|   |   -- plate_validator.py   Indian plate regex + normalisation
|   |-- services/
|   |   |-- webhook_client.py    Async POST to mana-community-service
|   |   |-- stream_manager.py    RTSP stream threads + ring-buffer
|   |   -- event_logger.py      SQLAlchemy async audit log
|   |-- api/routes/
|   |   |-- recognize.py         /recognize endpoints
|   |   |-- stream.py            /stream/start, /stream/stop
|   |   -- gates.py             /gates endpoints
|   |-- models/
|   |   |-- schemas.py           Pydantic request/response schemas
|   |   -- db_models.py         AnprGateEvent DB table
|   -- utils/
|       |-- image_utils.py       CLAHE + bilateral filter + adaptive threshold
|       -- logger.py            Structured JSON logging (structlog)
|-- models/                      Place YOLOv11 .pt weights here
|-- tests/
|   -- unit/
|       |-- test_plate_validator.py  10 tests
|       -- test_pipeline.py         6 tests (mocked detector + OCR)
|-- scripts/
|   |-- download_model.py        Download YOLOv11 weights from HuggingFace
|   -- test_camera.py           RTSP connectivity check
|-- docker/
|   |-- Dockerfile               CPU build
|   -- Dockerfile.gpu           NVIDIA CUDA 12.1 GPU build
|-- docker-compose.yml
|-- requirements.txt
|-- requirements-dev.txt
|-- .env.example
|-- pytest.ini
-- README.md
`

---

## Running Tests

`ash
pip install -r requirements-dev.txt
pytest
`

---

## Tech Stack

| Component | Library | Version |
|---|---|---|
| API Framework | FastAPI + Uvicorn | 0.115+ / 0.30+ |
| Plate Detection | ultralytics (YOLOv11) | 8.4+ |
| Primary OCR | EasyOCR | 1.7.2+ |
| Production OCR | PaddleOCR | 3.0+ |
| Computer Vision | OpenCV (headless) | 5.0+ |
| Async HTTP | httpx | 0.27+ |
| Database | SQLAlchemy async | 2.0+ |
| Logging | structlog | 24.4+ |
| Config | pydantic-settings | 2.5+ |

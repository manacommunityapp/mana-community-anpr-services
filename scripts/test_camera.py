"""
scripts/test_camera.py — Test RTSP stream connectivity for a gate camera.

Usage:
    python scripts/test_camera.py rtsp://admin:pass@192.168.1.101:554/stream1
    python scripts/test_camera.py --gate GATE_MAIN_IN  # reads from .env
"""
import sys
import time
import cv2


def test_rtsp(url: str, num_frames: int = 5) -> bool:
    print(f"Connecting to: {url}")
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("FAILED: Cannot open stream. Check URL, credentials, and network.")
        return False

    print(f"Connected! Reading {num_frames} frames...")
    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            print(f"FAILED: Frame {i + 1} read failed.")
            cap.release()
            return False
        h, w = frame.shape[:2]
        print(f"  Frame {i + 1}: {w}x{h} pixels OK")
        time.sleep(0.5)

    cap.release()
    print(f"SUCCESS: Stream is working. {num_frames} frames captured.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_camera.py <rtsp_url>")
        sys.exit(1)

    rtsp_url = sys.argv[1]
    ok = test_rtsp(rtsp_url)
    sys.exit(0 if ok else 1)

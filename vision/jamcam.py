# vision/jamcam.py
import base64
import math
import os
from dataclasses import dataclass
from typing import Optional
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from ingestor.tfl_client import Camera

load_dotenv()

_KEYWORDS = ["incident", "congested", "slow", "flowing"]
_MULTIPLIERS = {"incident": 1.4, "congested": 1.2, "slow": 1.1, "flowing": 1.0, "unknown": 1.0}

_PROMPT = (
    "This is a London traffic camera image. "
    "Classify the current traffic conditions using exactly one of these words: "
    "flowing, slow, congested, incident. "
    "Reply with that single word only."
)

def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def find_nearest_cameras(lat: float, lon: float, cameras: list[Camera], n: int = 3) -> list[Camera]:
    """Returns the n cameras closest to (lat, lon)."""
    scored = sorted(cameras, key=lambda c: _haversine(lat, lon, c.lat, c.lon))
    return scored[:n]

def parse_classification(text: str) -> str:
    """Extracts one of the four keywords from VLM response text."""
    t = text.strip().lower()
    for kw in _KEYWORDS:
        if kw in t:
            return kw
    return "unknown"

def severity_multiplier(classification: str) -> float:
    return _MULTIPLIERS.get(classification, 1.0)

def fetch_jpeg(url: str) -> Optional[bytes]:
    """Downloads a JPEG from a URL. Returns None on failure."""
    try:
        r = httpx.get(url, timeout=5.0)
        r.raise_for_status()
        return r.content
    except Exception:
        return None

def classify_camera(camera: Camera) -> str:
    """
    Fetches camera JPEG and calls local NIM VLM to classify traffic conditions.
    Returns one of: flowing, slow, congested, incident, unknown.
    """
    jpeg = fetch_jpeg(camera.image_url)
    if not jpeg:
        return "unknown"

    b64 = base64.b64encode(jpeg).decode("utf-8")
    client = OpenAI(
        base_url=os.getenv("NIM_BASE_URL", "http://localhost:8000/v1"),
        api_key="not-needed",
    )
    try:
        resp = client.chat.completions.create(
            model=os.getenv("NIM_MODEL", "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"),
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": _PROMPT},
            ]}],
            max_tokens=10,
        )
        return parse_classification(resp.choices[0].message.content or "")
    except Exception:
        return "unknown"

def classify_disruption(lat: float, lon: float, cameras: list[Camera]) -> tuple[str, Optional[str]]:
    """
    Finds the nearest camera to the disruption and classifies it.
    Returns (classification, image_url).
    """
    nearest = find_nearest_cameras(lat, lon, cameras, n=1)
    if not nearest:
        return "unknown", None
    cam = nearest[0]
    return classify_camera(cam), cam.image_url

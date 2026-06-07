# vision/jamcam.py
import math
import os
from typing import Optional
import httpx
from PIL import Image
import io
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

_MODEL_ID = os.getenv("HF_MODEL", "nvidia/llama-3.1-nemotron-nano-vl-8b-v1")

# Lazy-loaded model — only initialised on first classify_camera() call
_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor

    print(f"Loading VLM from HuggingFace: {_MODEL_ID} ...")
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText

    _processor = AutoProcessor.from_pretrained(_MODEL_ID, trust_remote_code=True)
    _model = AutoModelForImageTextToText.from_pretrained(
        _MODEL_ID,
        torch_dtype=torch.float16,
        device_map="cuda",
        trust_remote_code=True,
    )
    _model.eval()
    print("VLM ready.")
    return _model, _processor


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def find_nearest_cameras(lat: float, lon: float, cameras: list[Camera], n: int = 3) -> list[Camera]:
    """Returns the n cameras closest to (lat, lon)."""
    return sorted(cameras, key=lambda c: _haversine(lat, lon, c.lat, c.lon))[:n]


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
    Fetches camera JPEG and runs local Nemotron VL inference to classify traffic.
    Returns one of: flowing, slow, congested, incident, unknown.
    """
    jpeg = fetch_jpeg(camera.image_url)
    if not jpeg:
        return "unknown"

    try:
        import torch
        model, processor = _load_model()

        image = Image.open(io.BytesIO(jpeg)).convert("RGB")

        messages = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": _PROMPT},
            ]}
        ]

        text = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=text, images=image, return_tensors="pt").to("cuda")

        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=10, do_sample=False)

        decoded = processor.decode(output[0], skip_special_tokens=True)
        return parse_classification(decoded)

    except Exception as e:
        print(f"VLM inference failed: {e}")
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

import re
from dataclasses import dataclass
from typing import Optional
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

BASE = "https://api.tfl.gov.uk"
_POINT_RE = re.compile(r"POINT\(([^\s]+)\s+([^\)]+)\)")

@dataclass
class Disruption:
    id: str
    location: str
    comments: str
    lat: float
    lon: float
    start: str
    end: Optional[str]

@dataclass
class Camera:
    id: str
    lat: float
    lon: float
    image_url: str

class TflClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TFL_API_KEY", "")
        self._http = httpx.Client(timeout=15.0)

    def _params(self) -> dict:
        return {"app_key": self.api_key} if self.api_key else {}

    def get_disruptions(self) -> list[Disruption]:
        r = self._http.get(f"{BASE}/Road/all/Disruption", params=self._params())
        r.raise_for_status()
        out = []
        for d in r.json():
            point = d.get("point", "")
            m = _POINT_RE.search(point)
            if not m:
                continue
            lon, lat = float(m.group(1)), float(m.group(2))
            out.append(Disruption(
                id=d.get("id", ""),
                location=d.get("location", ""),
                comments=d.get("comments", ""),
                lat=lat,
                lon=lon,
                start=d.get("startDateTime", ""),
                end=d.get("endDateTime"),
            ))
        return out

    def get_cameras(self) -> list[Camera]:
        r = self._http.get(f"{BASE}/Road/all/Camera", params=self._params())
        r.raise_for_status()
        out = []
        for c in r.json():
            lat = c.get("lat")
            lon = c.get("lon")
            img = c.get("imageUrl", "")
            if lat is None or lon is None or not img:
                continue
            out.append(Camera(
                id=c.get("id", ""),
                lat=float(lat),
                lon=float(lon),
                image_url=img,
            ))
        return out

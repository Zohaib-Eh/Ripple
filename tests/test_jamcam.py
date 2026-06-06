# tests/test_jamcam.py
import pytest
import respx
import httpx
from unittest.mock import patch, MagicMock
from ingestor.tfl_client import Camera

FAKE_CAMERAS = [
    Camera(id="CAM-001", lat=51.5142, lon=-0.0918, image_url="http://fake.tfl.gov.uk/cam1.jpg"),
    Camera(id="CAM-002", lat=51.5200, lon=-0.1000, image_url="http://fake.tfl.gov.uk/cam2.jpg"),
    Camera(id="CAM-003", lat=51.5300, lon=-0.2000, image_url="http://fake.tfl.gov.uk/cam3.jpg"),
]

def test_find_nearest_cameras_returns_closest():
    from vision.jamcam import find_nearest_cameras
    # Query near CAM-001
    result = find_nearest_cameras(51.5140, -0.0920, FAKE_CAMERAS, n=2)
    assert result[0].id == "CAM-001"
    assert len(result) == 2

def test_find_nearest_cameras_respects_n():
    from vision.jamcam import find_nearest_cameras
    result = find_nearest_cameras(51.5142, -0.0918, FAKE_CAMERAS, n=1)
    assert len(result) == 1

def test_parse_classification_extracts_keyword():
    from vision.jamcam import parse_classification
    assert parse_classification("congested") == "congested"
    assert parse_classification("The traffic is flowing smoothly.") == "flowing"
    assert parse_classification("I see a major incident on the road.") == "incident"
    assert parse_classification("slow moving vehicles") == "slow"
    assert parse_classification("unclear image") == "unknown"

def test_severity_multiplier():
    from vision.jamcam import severity_multiplier
    assert severity_multiplier("incident") == 1.4
    assert severity_multiplier("congested") == 1.2
    assert severity_multiplier("slow") == 1.1
    assert severity_multiplier("flowing") == 1.0
    assert severity_multiplier("unknown") == 1.0

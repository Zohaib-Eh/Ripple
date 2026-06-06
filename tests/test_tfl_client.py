import pytest
import respx
import httpx
from ingestor.tfl_client import TflClient, Disruption, Camera

@pytest.fixture
def client():
    return TflClient(api_key="test-key")

@respx.mock
def test_get_disruptions_returns_list(client):
    respx.get("https://api.tfl.gov.uk/Road/all/Disruption").mock(
        return_value=httpx.Response(200, json=[
            {
                "id": "RDW-001",
                "location": "Cheapside, London",
                "comments": "Water main repair",
                "startDateTime": "2026-06-06T08:00:00Z",
                "endDateTime": "2026-06-06T18:00:00Z",
                "point": "POINT(-0.0918 51.5142)"
            }
        ])
    )
    result = client.get_disruptions()
    assert len(result) == 1
    assert isinstance(result[0], Disruption)
    assert result[0].id == "RDW-001"
    assert abs(result[0].lat - 51.5142) < 0.001
    assert abs(result[0].lon - (-0.0918)) < 0.001

@respx.mock
def test_get_disruptions_empty(client):
    respx.get("https://api.tfl.gov.uk/Road/all/Disruption").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = client.get_disruptions()
    assert result == []

@respx.mock
def test_get_cameras_returns_list(client):
    respx.get("https://api.tfl.gov.uk/Road/all/Camera").mock(
        return_value=httpx.Response(200, json=[
            {
                "id": "CAM-001",
                "lat": 51.5142,
                "lon": -0.0918,
                "imageUrl": "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/CAM-001.jpg"
            }
        ])
    )
    result = client.get_cameras()
    assert len(result) == 1
    assert isinstance(result[0], Camera)
    assert result[0].id == "CAM-001"
    assert result[0].image_url == "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/CAM-001.jpg"

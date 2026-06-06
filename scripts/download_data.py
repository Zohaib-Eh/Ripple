"""
Run this once to download all static London datasets.
Usage: python scripts/download_data.py
"""
import os
import requests
import zipfile
import io
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def download_file(url: str, dest: Path, description: str):
    print(f"Downloading {description}...")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  Saved to {dest} ({dest.stat().st_size // 1024} KB)")

def download_zip(url: str, dest_dir: Path, description: str):
    print(f"Downloading {description}...")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(dest_dir)
    print(f"  Extracted to {dest_dir}/")

# 1. London LSOA boundaries (GeoJSON for spatial join)
download_file(
    "https://data.london.gov.uk/download/statistical-gis-boundary-files-london/9ba8c833-6370-4b11-abdc-314aa020d867/statistical-gis-boundaries-london.zip",
    DATA_DIR / "lsoa_boundaries.zip",
    "LSOA boundaries (zip)"
)
with zipfile.ZipFile(DATA_DIR / "lsoa_boundaries.zip") as z:
    z.extractall(DATA_DIR / "lsoa_boundaries")
print("  Extracted LSOA boundaries")

# 2. LSOA Atlas (demographics CSV)
download_file(
    "https://data.london.gov.uk/download/lsoa-atlas/b8e9-wm9k/lsoa-data-2015.csv",
    DATA_DIR / "lsoa_atlas.csv",
    "LSOA Atlas demographics"
)

# 3. Bus Stop Locations and Usage
download_file(
    "https://data.london.gov.uk/download/bus-stop-locations-and-usage/7a12a3a0-30c5-4c96-960e-1e3ee71741e0/bus-stop-locations-and-usage.csv",
    DATA_DIR / "bus_stops.csv",
    "Bus stop locations and usage"
)

# 4. IMD 2019 London
download_file(
    "https://data.london.gov.uk/download/indices-of-deprivation/d9f5f1b3-2a93-4e0a-82a6-77d3a3a90f1b/ID2019_London.csv",
    DATA_DIR / "imd_2019.csv",
    "Index of Multiple Deprivation 2019"
)

# 5. Business counts by borough (proxy: use ONS data)
download_file(
    "https://data.london.gov.uk/download/business-demographics-and-survival-rates-borough/fbe5-3c1f/business-demographics.csv",
    DATA_DIR / "business_counts.csv",
    "Business counts by borough"
)

print("\nAll datasets downloaded. Now downloading road network via OSMnx...")
print("Run: python scripts/download_road_network.py")

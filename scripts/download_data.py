"""
Run this once to download all static London datasets.
Usage: python scripts/download_data.py
"""
import requests
import zipfile
import io
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

def download_file(url: str, dest: Path, description: str):
    if dest.exists():
        print(f"Skipping {description} (already exists)")
        return
    print(f"Downloading {description}...")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  Saved to {dest} ({dest.stat().st_size // 1024} KB)")

# 1. London LSOA boundaries (GeoJSON for spatial join)
lsoa_zip = DATA_DIR / "lsoa_boundaries.zip"
lsoa_dir = DATA_DIR / "lsoa_boundaries"
if not lsoa_dir.exists():
    download_file(
        "https://data.london.gov.uk/download/20od9/9ba8c833-6370-4b11-abdc-314aa020d5e0/statistical-gis-boundaries-london.zip",
        lsoa_zip,
        "LSOA boundaries (zip)"
    )
    with zipfile.ZipFile(lsoa_zip) as z:
        z.extractall(lsoa_dir)
    print("  Extracted LSOA boundaries")
    lsoa_zip.unlink()
    print("  Removed zip file")
else:
    print("Skipping LSOA boundaries (already exists)")

# 2. LSOA Atlas (demographics CSV)
download_file(
    "https://data.london.gov.uk/download/2n8zy/0193f884-2ccd-49c2-968e-28aa3b1c480d/lsoa-data.csv",
    DATA_DIR / "lsoa_atlas.csv",
    "LSOA Atlas demographics"
)

# 3. Bus Stop Locations and Usage
download_file(
    "https://data.london.gov.uk/download/e68zn/673033eb-59a6-4903-84bc-d24495661707/bus-stops-10-06-15.csv",
    DATA_DIR / "bus_stops.csv",
    "Bus stop locations and usage"
)

# 4. IMD 2019 London (source is XLSX, convert to CSV)
imd_csv = DATA_DIR / "imd_2019.csv"
if not imd_csv.exists():
    imd_xlsx = DATA_DIR / "imd_2019.xlsx"
    download_file(
        "https://data.london.gov.uk/download/2l15g/9ee0cf66-e6f9-4e38-8eec-79c1d897e248/ID%202019%20for%20London.xlsx",
        imd_xlsx,
        "Index of Multiple Deprivation 2019 (xlsx)"
    )
    print("  Converting IMD xlsx to csv...")
    df = pd.read_excel(imd_xlsx, sheet_name=0)
    df.to_csv(imd_csv, index=False)
    imd_xlsx.unlink()
    print(f"  Saved to {imd_csv}")
else:
    print("Skipping Index of Multiple Deprivation 2019 (already exists)")

# 5. Business counts by borough (proxy: use ONS data)
download_file(
    "https://data.london.gov.uk/download/ep8ny/afcc168c-d8ca-4d42-8f16-3d626d1c384d/business-demographics.csv",
    DATA_DIR / "business_counts.csv",
    "Business counts by borough"
)

print("\nAll datasets downloaded. Now downloading road network via OSMnx...")
print("Run: python scripts/download_road_network.py")

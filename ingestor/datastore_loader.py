"""
Loads static London datasets from data/ into cuDF DataFrames.
Also runs the one-time spatial join: bus stops → LSOA codes.
Call load_all() once at startup.
"""
from pathlib import Path
import cudf
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

DATA = Path("data")

def load_bus_stops() -> cudf.DataFrame:
    """
    Returns cuDF with columns: stop_id, stop_name, lat, lon, daily_boardings
    """
    df = pd.read_csv(DATA / "bus_stops.csv", low_memory=False)
    # Normalise column names — London Datastore uses varying headers
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    # Best-effort column mapping
    col_map = {}
    for c in df.columns:
        if "id" in c and "stop" in c:
            col_map[c] = "stop_id"
        elif "name" in c:
            col_map[c] = "stop_name"
        elif "lat" in c:
            col_map[c] = "lat"
        elif "lon" in c or "lng" in c or "long" in c:
            col_map[c] = "lon"
        elif "board" in c:
            col_map[c] = "daily_boardings"
    df = df.rename(columns=col_map)
    needed = [c for c in ["stop_id", "stop_name", "lat", "lon", "daily_boardings"] if c in df.columns]
    df = df[needed].dropna(subset=["lat", "lon"])
    return cudf.from_pandas(df)

def load_lsoa_demographics() -> cudf.DataFrame:
    """
    Returns cuDF with columns: lsoa_code, lsoa_name, population, imd_decile
    """
    atlas = pd.read_csv(DATA / "lsoa_atlas.csv", low_memory=False)
    atlas.columns = [c.strip().lower().replace(" ", "_") for c in atlas.columns]
    imd = pd.read_csv(DATA / "imd_2019.csv", low_memory=False)
    imd.columns = [c.strip().lower().replace(" ", "_") for c in imd.columns]

    # Extract LSOA code and IMD decile
    lsoa_col = next((c for c in imd.columns if "lsoa" in c and "code" in c), imd.columns[0])
    decile_col = next((c for c in imd.columns if "decile" in c), None)

    if decile_col:
        imd_slim = imd[[lsoa_col, decile_col]].rename(columns={lsoa_col: "lsoa_code", decile_col: "imd_decile"})
    else:
        imd_slim = imd[[lsoa_col]].rename(columns={lsoa_col: "lsoa_code"})
        imd_slim["imd_decile"] = 5  # fallback

    # Extract population from atlas
    pop_col = next((c for c in atlas.columns if "popul" in c), None)
    code_col = next((c for c in atlas.columns if "lsoa" in c and "code" in c), atlas.columns[0])
    name_col = next((c for c in atlas.columns if "name" in c), None)

    if pop_col:
        keep = [code_col, name_col, pop_col] if name_col else [code_col, pop_col]
        atlas_slim = atlas[keep].rename(columns={code_col: "lsoa_code", name_col: "lsoa_name", pop_col: "population"})
    else:
        atlas_slim = atlas[[code_col]].rename(columns={code_col: "lsoa_code"})
        atlas_slim["population"] = 1500  # fallback

    merged = atlas_slim.merge(imd_slim, on="lsoa_code", how="left")
    merged["imd_decile"] = merged["imd_decile"].fillna(5)
    return cudf.from_pandas(merged)

def load_business_counts() -> cudf.DataFrame:
    """
    Returns cuDF with columns: borough, business_count
    Borough-level only — will be joined to LSOAs via borough lookup.
    """
    df = pd.read_csv(DATA / "business_counts.csv", low_memory=False)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    borough_col = next((c for c in df.columns if "borough" in c or "area" in c), df.columns[0])
    count_col = next((c for c in df.columns if "count" in c or "total" in c or "number" in c), df.columns[1])
    df = df[[borough_col, count_col]].rename(columns={borough_col: "borough", count_col: "business_count"})
    return cudf.from_pandas(df)

def join_stops_to_lsoa(stops_cudf: cudf.DataFrame) -> cudf.DataFrame:
    """
    Spatial join: assigns each bus stop its LSOA code.
    Runs once at startup using GeoPandas (cuSpatial not required).
    Returns stops_cudf with added 'lsoa_code' column.
    """
    cache = DATA / "stops_with_lsoa.parquet"
    if cache.exists():
        print("Loading stops→LSOA cache from parquet...")
        return cudf.read_parquet(cache)

    print("Running spatial join: stops → LSOA (one-time, ~30s)...")
    lsoa_boundaries = gpd.read_file(DATA / "lsoa_boundaries")
    lsoa_boundaries = lsoa_boundaries.to_crs("EPSG:4326")
    lsoa_col = next((c for c in lsoa_boundaries.columns if "lsoa" in c.lower() and "code" in c.lower()), "LSOA11CD")

    stops_pd = stops_cudf.to_pandas()
    stops_gdf = gpd.GeoDataFrame(
        stops_pd,
        geometry=[Point(lon, lat) for lon, lat in zip(stops_pd["lon"], stops_pd["lat"])],
        crs="EPSG:4326"
    )
    joined = gpd.sjoin(stops_gdf, lsoa_boundaries[[lsoa_col, "geometry"]], how="left", predicate="within")
    joined = joined.rename(columns={lsoa_col: "lsoa_code"})
    joined = joined.drop(columns=["geometry", "index_right"], errors="ignore")

    result = cudf.from_pandas(joined.drop(columns=["geometry"], errors="ignore").reset_index(drop=True))
    result.to_parquet(cache)
    print(f"Spatial join complete. {len(result)} stops assigned to LSOAs.")
    return result

def load_all() -> dict:
    """Entry point. Returns dict of all DataFrames."""
    print("Loading London Datastore datasets...")
    stops = load_bus_stops()
    stops = join_stops_to_lsoa(stops)
    demographics = load_lsoa_demographics()
    businesses = load_business_counts()
    print(f"  Bus stops: {len(stops)} rows")
    print(f"  LSOA demographics: {len(demographics)} rows")
    print(f"  Business counts: {len(businesses)} rows")
    return {
        "stops": stops,
        "demographics": demographics,
        "businesses": businesses,
    }

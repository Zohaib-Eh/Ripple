"""
Downloads Central London road network via OSMnx and saves as GraphML.
Takes 3-5 minutes. Run separately.
Usage: python scripts/download_road_network.py
"""
import osmnx as ox
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT = DATA_DIR / "london_road_network.graphml"

if OUT.exists():
    print(f"Already exists: {OUT}")
else:
    print("Downloading Central London road network (drive mode)...")
    # Bounding box: Central/Inner London only (keeps graph manageable ~25k nodes)
    G = ox.graph_from_bbox(
        north=51.560, south=51.460,
        east=-0.050, west=-0.250,
        network_type="drive",
        simplify=True
    )
    print(f"Graph: {len(G.nodes)} nodes, {len(G.edges)} edges")
    ox.save_graphml(G, OUT)
    print(f"Saved to {OUT}")

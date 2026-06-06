# main.py
"""
Ripple — main entry point.
Loads all data at startup, then runs the live 30-second poll loop.
Usage: streamlit run main.py
"""
import time
import streamlit as st
from ingestor.tfl_client import TflClient, Disruption
from ingestor.datastore_loader import load_all
from graph.builder import load_graph, nearest_node
from graph.cascade import run_cascade
from impact.enricher import compute_impact
from vision.jamcam import classify_disruption, severity_multiplier
from ui.app import render
import cudf
import pandas as pd

# --- Bank Station Demo Scenario ---
# Coordinates: Bank Station, City of London
BANK_STATION_DEMO: dict = {
    "id": "DEMO-BANK-001",
    "location": "Bank Station, King William St, London",
    "comments": "Simulated: Northern Line + Central Line suspension due to engineering works",
    "lat": 51.5133,
    "lon": -0.0886,
    "start": "2026-06-06T07:00:00Z",
    "end": "2026-06-06T20:00:00Z",
}

@st.cache_resource
def startup():
    """Load all static data and graph. Cached so Streamlit only runs this once."""
    data = load_all()
    G_cu, int_to_node, node_positions = load_graph()

    # Assign nearest graph node to each bus stop (one-time at startup)
    stops_pd = data["stops"].to_pandas()
    stops_pd["node_id"] = stops_pd.apply(
        lambda r: nearest_node(r["lat"], r["lon"], node_positions), axis=1
    )
    data["stops"] = cudf.from_pandas(stops_pd)

    client = TflClient()
    return data, G_cu, node_positions, client

def process_disruption(
    d: dict,
    G_cu,
    node_positions,
    data: dict,
    cameras,
) -> dict:
    """Runs cascade + enrichment + vision for a single disruption."""
    start_node = nearest_node(d["lat"], d["lon"], node_positions)
    affected = run_cascade(G_cu, start_node=start_node, max_depth=15)

    impact = compute_impact(
        affected_nodes=affected,
        stops=data["stops"],
        demographics=data["demographics"],
        businesses=data["businesses"],
    )

    vision, img_url = classify_disruption(d["lat"], d["lon"], cameras)
    mult = severity_multiplier(vision)
    impact["journeys_affected"] = int(impact["journeys_affected"] * mult)

    return {**d, "impact": impact, "vision": vision, "image_url": img_url}

def main():
    data, G_cu, node_positions, client = startup()

    # Get cameras once per session (they don't change often)
    if "cameras" not in st.session_state:
        st.session_state.cameras = client.get_cameras()

    # Demo button
    if st.sidebar.button("Demo: Bank Station Closure", key="main_demo"):
        st.session_state.use_demo = True
    if st.sidebar.button("Live Mode"):
        st.session_state.use_demo = False

    if st.session_state.get("use_demo", False):
        raw_disruptions = [BANK_STATION_DEMO]
    else:
        try:
            disruptions = client.get_disruptions()
            raw_disruptions = [
                {"id": d.id, "location": d.location, "comments": d.comments,
                 "lat": d.lat, "lon": d.lon, "start": d.start, "end": d.end}
                for d in disruptions
            ]
        except Exception as e:
            st.warning(f"TfL API error: {e}")
            raw_disruptions = []

    results = []
    for d in raw_disruptions:
        try:
            results.append(process_disruption(d, G_cu, node_positions, data, st.session_state.cameras))
        except Exception as e:
            st.warning(f"Error processing disruption {d.get('id')}: {e}")

    render(results)

    if st.session_state.get("auto_refresh", True):
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()

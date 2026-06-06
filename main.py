# main.py
"""
Ripple — main entry point.
Loads all data at startup, then runs the live 30-second poll loop.
Usage: streamlit run main.py
"""
import time
import streamlit as st
from ingestor.tfl_client import TflClient
from ingestor.datastore_loader import load_all
from graph.builder import load_graph, nearest_node
from graph.cascade import run_cascade
from impact.enricher import compute_impact
from vision.jamcam import classify_disruption, severity_multiplier
from ui.app import render
import cudf
import pandas as pd


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


def process_disruption(d: dict, G_cu, node_positions, data: dict, cameras) -> dict:
    """Runs cascade + enrichment + vision for a single disruption."""
    start_node = nearest_node(d["lat"], d["lon"], node_positions)
    affected = run_cascade(G_cu, start_node=start_node, max_depth=15)

    impact = compute_impact(
        affected_nodes=affected,
        stops=data["stops"],
        demographics=data["demographics"],
        businesses=data["businesses"],
    )

    if d.get("planned"):
        # Planned disruptions: still fetch nearest camera for context, but don't
        # adjust severity — there's no observed congestion yet, this is a forecast.
        _, img_url = classify_disruption(d["lat"], d["lon"], cameras)
        vision = "planned"
    else:
        vision, img_url = classify_disruption(d["lat"], d["lon"], cameras)
        mult = severity_multiplier(vision)
        impact["journeys_affected"] = int(impact["journeys_affected"] * mult)

    return {**d, "impact": impact, "vision": vision, "image_url": img_url}


def main():
    data, G_cu, node_positions, client = startup()

    if "cameras" not in st.session_state:
        st.session_state.cameras = client.get_cameras()

    # --- Fetch live TfL disruptions ---
    try:
        disruptions = client.get_disruptions()
        raw_disruptions = [
            {
                "id": d.id,
                "location": d.location,
                "comments": d.comments,
                "lat": d.lat,
                "lon": d.lon,
                "start": d.start,
                "end": d.end,
                "planned": False,
            }
            for d in disruptions
        ]
    except Exception as e:
        st.warning(f"TfL API error: {e}")
        raw_disruptions = []

    # --- Add planned disruption from session state (if set) ---
    planned_pending = None
    planned = st.session_state.get("planned_disruption")
    if planned:
        raw_disruptions.append(planned)

    # --- Process all disruptions through the pipeline ---
    results = []
    for d in raw_disruptions:
        try:
            results.append(process_disruption(d, G_cu, node_positions, data, st.session_state.cameras))
        except Exception as e:
            st.warning(f"Error processing {d.get('id', 'disruption')}: {e}")

    # --- Render UI, get map click data ---
    map_data = render(results, planned_pending=planned_pending)

    # --- Handle map click: set new planned disruption ---
    if map_data and map_data.get("last_clicked"):
        click = map_data["last_clicked"]
        description = st.session_state.get("plan_description", "Planned disruption")
        dtype = st.session_state.get("plan_type", "Road Closure")
        st.session_state.planned_disruption = {
            "id": "PLANNED-001",
            "location": f"{dtype} at ({click['lat']:.4f}, {click['lng']:.4f})",
            "comments": description,
            "lat": click["lat"],
            "lon": click["lng"],
            "start": "",
            "end": "",
            "planned": True,
        }
        st.rerun()

    # --- Auto-refresh for live data ---
    if st.session_state.get("auto_refresh", True):
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()

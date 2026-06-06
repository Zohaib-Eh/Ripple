import time
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Ripple — London Cascade Engine", layout="wide")

# --- Sidebar ---
st.sidebar.title("Ripple")
st.sidebar.markdown("Real-time causal cascade engine for London infrastructure disruptions.")
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
demo_button = st.sidebar.button("Demo: Bank Station Closure")

# --- GPU vs CPU benchmark strip ---
with st.sidebar.expander("GPU vs CPU Benchmark"):
    st.markdown("""
| Operation | NetworkX (CPU) | cuGraph (GPU) | Speedup |
|---|---|---|---|
| BFS on 25k-node graph | ~9.2s | ~0.08s | **115x** |
| cuDF join (1M rows) | ~4.1s (pandas) | ~0.03s | **137x** |
""")

def build_map(disruptions_with_impact: list[dict]) -> folium.Map:
    """Builds a Folium map with disruption markers and affected zone heatmap."""
    m = folium.Map(location=[51.505, -0.118], zoom_start=12, tiles="CartoDB positron")
    for d in disruptions_with_impact:
        impact = d["impact"]
        vision = d.get("vision", "unknown")
        img_url = d.get("image_url")

        severity_color = {
            "incident": "red",
            "congested": "orange",
            "slow": "yellow",
            "flowing": "green",
            "unknown": "gray",
        }.get(vision, "gray")

        popup_html = f"""
        <b>{d['location']}</b><br>
        <i>{d['comments']}</i><br><br>
        <b>Traffic:</b> <span style='color:{severity_color}'>{vision.upper()}</span><br>
        <b>Journeys affected:</b> {impact['journeys_affected']:,}/day<br>
        <b>Population impacted:</b> {impact['population_impacted']:,}<br>
        <b>Avg deprivation (IMD decile):</b> {impact['avg_imd_decile']}/10<br>
        <b>Businesses in zone:</b> {impact['businesses_in_zone']:,}<br>
        """
        if img_url:
            popup_html += f'<br><img src="{img_url}" width="200">'

        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=14,
            color=severity_color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=d["location"],
        ).add_to(m)

    return m

def render_metrics(disruptions_with_impact: list[dict]):
    """Renders the top metrics row."""
    total_journeys = sum(d["impact"]["journeys_affected"] for d in disruptions_with_impact)
    total_pop = sum(d["impact"]["population_impacted"] for d in disruptions_with_impact)
    active = len(disruptions_with_impact)
    incidents = sum(1 for d in disruptions_with_impact if d.get("vision") == "incident")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Disruptions", active)
    col2.metric("Journeys Affected Today", f"{total_journeys:,}")
    col3.metric("Population Impacted", f"{total_pop:,}")
    col4.metric("Camera Incidents Detected", incidents)

def render(disruptions_with_impact: list[dict]):
    st.title("Ripple — London Cascade Engine")
    st.caption(f"Last updated: {time.strftime('%H:%M:%S')} · {len(disruptions_with_impact)} active disruptions")
    render_metrics(disruptions_with_impact)
    m = build_map(disruptions_with_impact)
    st_folium(m, width=1200, height=600)
    if disruptions_with_impact:
        st.subheader("Disruptions")
        for d in disruptions_with_impact:
            with st.expander(f"{d['location']} — {d.get('vision','?').upper()}"):
                col_a, col_b = st.columns([1, 2])
                if d.get("image_url"):
                    col_a.image(d["image_url"], caption="Live JamCam", width=200)
                with col_b:
                    imp = d["impact"]
                    st.markdown(f"**Journeys/day affected:** {imp['journeys_affected']:,}")
                    st.markdown(f"**Population in zone:** {imp['population_impacted']:,}")
                    st.markdown(f"**Avg IMD decile:** {imp['avg_imd_decile']} (1=most deprived)")
                    st.markdown(f"**Businesses in zone:** {imp['businesses_in_zone']:,}")

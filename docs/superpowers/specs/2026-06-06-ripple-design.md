# Ripple — Design Spec
**Date:** 2026-06-06  
**Track:** Urban Operations  
**Constraint:** Solo build, 6–7 hours, DGX Spark (remote SSH)

---

## Problem

London makes thousands of infrastructure decisions per year — roadworks, bus diversions, line suspensions — each approved in isolation. A road closure approved by one council officer has no visibility into the 8,000 daily journeys that route through that street, the buses that will run late, the businesses that will lose footfall, or the workers who will arrive late. The data to see this exists. It lives in separate systems that have never talked to each other.

## What Ripple Does

A real-time causal cascade engine that:
1. Ingests live TfL disruption data every 30 seconds
2. Models the downstream human impact using GPU-accelerated graph BFS on the London transport network
3. Validates the modelled impact against live JamCam footage via a local Vision Language Model
4. Surfaces results on a live map with four human-readable impact metrics

Everything runs locally on the DGX Spark — no cloud APIs, no external LLM calls.

---

## Architecture

### Startup (once)
- Download London Road Network shapefile → parse into cuGraph (nodes = intersections + bus stops + tube stations, edges = road segments + transit links)
- Load into cuDF: bus stop boarding counts, LSOA Atlas + IMD deprivation index, business counts by borough
- GeoPandas spatial join: assign each bus stop an LSOA code → convert result to cuDF

### Live Loop (every 30 seconds)
1. Poll `TfL /Road/all/Disruption` → get active road disruptions
2. Poll `TfL /Road/all/Camera` → get JamCam positions
3. For each new or changed disruption:
   - Find nearest graph nodes to disruption coordinates
   - Run **cuGraph BFS** (depth ≤ 15 hops) → affected node set
   - **cuDF joins:** affected stops → boarding counts → sum estimated daily journeys; affected stops → LSOA codes → demographics → sum population, avg IMD decile, sum business count
   - Fetch 3–5 nearest JamCam JPEGs
   - Send to **local NIM VLM** (`microsoft/phi-3.5-vision-instruct`) with prompt: *"This is a London traffic camera. Classify conditions: flowing / slow / congested / incident. One word only."*
   - If vision classification = `incident` → multiply impact severity ×1.4
4. Push updated state to Streamlit

### UI
- **Folium map:** disruption markers (red), affected zone heatmap
- **Click any disruption:** side panel opens with camera thumbnail + classification badge + four metrics
- **Four impact metrics:** estimated affected daily journeys, population in impacted LSOAs, average IMD deprivation decile, business count in affected zone
- **"Demo: Bank Station Closure"** button — hardcoded historical scenario with real numbers
- **GPU vs CPU timing strip** — precomputed BFS benchmark (NetworkX vs cuGraph on same graph)

---

## NVIDIA Stack

| Tool | Role |
|---|---|
| **cuDF** (RAPIDS) | GPU-accelerated DataFrame joins across all London datasets |
| **cuGraph** (RAPIDS) | GPU-accelerated BFS cascade simulation on transport graph |
| **NVIDIA NIM** | Local VLM inference on JamCam JPEGs (phi-3.5-vision-instruct) |

**Spark Story:** "We use cuGraph to run BFS across London's 80,000-node transport graph in under 100ms — the same operation with NetworkX takes 8–12 seconds on CPU. We run VLM inference locally on the DGX Spark's 128GB unified memory, meaning live camera footage never leaves the network."

---

## File Structure

```
ripple/
├── data/                    # cached London Datastore files (gitignored)
├── ingestor/
│   ├── tfl_client.py        # TfL API polling
│   └── datastore_loader.py  # one-time London Datastore load
├── graph/
│   ├── builder.py           # shapefile → cuGraph
│   └── cascade.py           # BFS + hop-distance scoring
├── vision/
│   └── jamcam.py            # JPEG fetch + NIM VLM inference
├── impact/
│   └── enricher.py          # cuDF joins for impact metrics
├── ui/
│   └── app.py               # Streamlit + Folium
└── main.py                  # poll loop + wiring
```

---

## Time Budget

| Block | Time | Task |
|---|---|---|
| 1 | 0:00–0:30 | DGX Spark env: RAPIDS install, NIM container pull, TfL API key |
| 2 | 0:30–1:30 | `datastore_loader.py` + `tfl_client.py` — data in, verify shapes |
| 3 | 1:30–2:30 | `builder.py` — shapefile → cuGraph, spatial join stops→LSOA |
| 4 | 2:30–3:30 | `cascade.py` + `enricher.py` — BFS + cuDF impact joins |
| 5 | 3:30–4:30 | `jamcam.py` — JPEG fetch, NIM inference, severity adjustment |
| 6 | 4:30–5:30 | `app.py` — Streamlit + Folium, click panel, metrics |
| 7 | 5:30–6:15 | Integration + Bank Station demo scenario |
| 8 | 6:15–7:00 | CPU vs GPU benchmark strip, polish, full flow test |

---

## Data Sources

### TfL Unified API (live, 30s poll)
- `/Road/all/Disruption` — active road disruptions
- `/Road/all/Camera` — JamCam positions + JPEG URLs
- `/Vehicle/EmitNoPredictions/{ids}` — live bus positions (optional enrichment)

### London Datastore (downloaded at startup)
- London Road Network — street geometry (shapefile)
- Bus Stop Locations and Usage — stop-level boarding/alighting counts
- LSOA Atlas — demographic data by small area
- Average Public Transport Accessibility Levels (PTAL)
- Recorded Crime by Borough
- Business Counts by Borough

---

## Key Risks

| Risk | Mitigation |
|---|---|
| NIM container setup time | Pull container during env setup (Block 1); fallback: skip vision, use bus delay proxy |
| Road network shapefile format | Use OSMnx as fallback to generate London graph from OpenStreetMap |
| LSOA spatial join performance | Run once at startup with GeoPandas, cache result as parquet, load into cuDF |
| cuGraph BFS scope | Cap BFS at depth 15 to bound runtime; tune if needed |
| TfL API rate limits | Register for free API key; cache responses; 30s poll is well within limits |

---

## Impact Metrics Definition

- **Journeys affected:** sum of daily boardings at BFS-reachable bus stops (proxy for disrupted journeys)
- **Population impacted:** sum of LSOA population within BFS-reachable area
- **Deprivation score:** population-weighted average IMD decile of affected LSOAs (lower = more deprived)
- **Businesses in zone:** count of registered businesses in affected LSOAs

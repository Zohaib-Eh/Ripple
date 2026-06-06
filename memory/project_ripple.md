---
name: project-ripple
description: Ripple hackathon project — real-time London infrastructure cascade engine on DGX Spark
metadata:
  type: project
---

Ripple is a real-time causal cascade engine for London infrastructure disruptions. Solo fallback project for an NVIDIA hackathon with 6-7 hour build time.

**Why:** Team's main project wasn't interesting to the user; Ripple is the fallback.

**Stack:** RAPIDS (cuDF + cuGraph), NVIDIA NIM (phi-3.5-vision-instruct), OSMnx, GeoPandas, Streamlit, Folium

**Key components:**
- cuGraph BFS cascade from disruption nodes on London road network
- cuDF joins against LSOA demographics, bus boarding counts, business data
- JamCam JPEG fetch + local NIM VLM for traffic classification
- Streamlit + Folium live map with impact metrics panel

**Design doc:** `docs/superpowers/specs/2026-06-06-ripple-design.md`
**Implementation plan:** `docs/superpowers/plans/2026-06-06-ripple.md`

**DGX Spark:** `ssh nvidia@hp-15.local` — [[reference-dgx-spark]]

**How to apply:** Start implementation from Task 0 (data download) of the plan.

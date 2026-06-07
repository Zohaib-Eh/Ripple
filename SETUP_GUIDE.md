# How to Run Ripple on the DGX Spark

Everything you need, step by step. No prior experience required.

---

## Overview

Your code is on your Windows laptop. The DGX Spark is a separate machine you connect to via SSH (`ssh nvidia@hp-15.local`). You need to:

1. Copy the code from your laptop to the Spark
2. Set up the environment on the Spark
3. Download the London data
4. Start the NIM AI model container
5. Run the app
6. View it in your browser

---

## Step 1 — Copy the Code to the DGX Spark

On your **Windows machine**, open PowerShell and run:

```powershell
scp -r "C:\Users\zohai\Projects\NVIDIA" nvidia@hp-15.local:~/ripple
```

This copies your entire project folder to a folder called `ripple` on the Spark. It will ask for a password if one is set.

**Verify it worked** — SSH into the Spark and check:
```bash
ssh nvidia@hp-15.local
ls ~/ripple
```

You should see files like `main.py`, `requirements.txt`, `RIPPLE.md`, etc.

---

## Step 2 — Stay Connected with Port Forwarding

You need to view the Streamlit app in your browser. To do that, open a **new PowerShell window** and connect like this:

```powershell
ssh -L 8501:localhost:8501 nvidia@hp-15.local
```

The `-L 8501:localhost:8501` part creates a tunnel — anything running on port 8501 on the Spark will be accessible at `http://localhost:8501` in your browser on Windows.

**Keep this terminal open the entire time.** Don't close it.

---

## Step 3 — Set Up Python Environment on the Spark

In your SSH session, run:

```bash
cd ~/ripple
```

Check Python version (needs 3.10+):
```bash
python3 --version
```

Install all dependencies. RAPIDS (cuDF/cuGraph) needs the NVIDIA PyPI index:

```bash
pip install cudf-cu12 cugraph-cu12 --extra-index-url=https://pypi.nvidia.com
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate osmnx geopandas shapely httpx streamlit folium streamlit-folium python-dotenv networkx pillow pandas pytest respx
```

This will take 5–10 minutes. The RAPIDS and PyTorch packages are large.

**Verify RAPIDS installed correctly:**
```bash
python3 -c "import cudf; import cugraph; print('RAPIDS OK')"
```

If you see `RAPIDS OK` you're good. If it errors, run:
```bash
pip install cudf-cu12 cugraph-cu12 --extra-index-url=https://pypi.nvidia.com --upgrade
```

---

## Step 4 — Get Your TfL API Key

1. Go to **https://api.tfl.gov.uk** in your browser
2. Click **Register** (top right)
3. Fill in your details — it's free and instant
4. Once logged in, go to **My Account** → **API Keys**
5. Copy your key

You'll need this in Step 7.

---

## Step 5 — Pre-download the VLM Model Weights

The vision model (`nvidia/llama-3.1-nemotron-nano-vl-8b-v1`) is downloaded from HuggingFace the first time the app runs a camera classification. To avoid a cold-start delay during the demo, pre-download it now:

```bash
python3 -c "
from transformers import AutoProcessor, AutoModelForImageTextToText
import torch
model_id = 'nvidia/llama-3.1-nemotron-nano-vl-8b-v1'
print('Downloading processor...')
AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
print('Downloading model weights (this takes a few minutes)...')
AutoModelForImageTextToText.from_pretrained(model_id, torch_dtype=torch.float16, device_map='cuda', trust_remote_code=True)
print('Done — model cached.')
"
```

This downloads ~16GB of weights into `~/.cache/huggingface/`. It only runs once — subsequent loads use the cache and take ~30 seconds.

---

## Step 6 — Download the London Data

Still in your SSH session (`cd ~/ripple`), run:

```bash
pip install requests osmnx
python3 scripts/download_data.py
```

This downloads LSOA boundaries, bus stops, demographics, and business counts. Takes about 2–3 minutes.

Then download the road network (this one takes longer — 4–6 minutes):

```bash
python3 scripts/download_road_network.py
```

You should see output like:
```
Downloading Central London road network (drive mode)...
Graph: 24891 nodes, 58432 edges
Saved to data/london_road_network.graphml
```

**Verify everything downloaded:**
```bash
ls data/
```

You should see: `lsoa_boundaries/`, `lsoa_atlas.csv`, `bus_stops.csv`, `imd_2019.csv`, `business_counts.csv`, `london_road_network.graphml`

---

## Step 7 — Create Your .env File

This file holds your secret keys. In your SSH session:

```bash
cd ~/ripple
nano .env
```

The `.env` file was already copied across with your code. Open it and fill in the two keys:

```bash
cd ~/ripple
nano .env
```

It should look like this (your TfL key is already there):

```
TFL_API_KEY=your_tfl_key_here
NGC_API_KEY=your_ngc_key_here
```

The `NIM_BASE_URL` and `NIM_MODEL` lines are no longer needed — the model loads directly via HuggingFace.

Save and exit: press `Ctrl+X`, then `Y`, then `Enter`.

---

## Step 8 — Run the Ripple App

Go back to your **first SSH session** (the one with port forwarding: `ssh -L 8501:...`):

```bash
cd ~/ripple
streamlit run main.py --server.port 8501 --server.address 0.0.0.0
```

You'll see:
```
  You can now view your Streamlit app in your browser.
  Network URL: http://0.0.0.0:8501
```

---

## Step 9 — Open in Your Browser

On your **Windows laptop**, open your browser and go to:

```
http://localhost:8501
```

You should see the Ripple map! The first load takes 2–3 minutes because it's:
- Loading the London road network into cuGraph (GPU)
- Running the spatial join to assign LSOA codes to bus stops
- Fetching live data from TfL

After the first load, refreshes are fast.

---

## What You'll See

- **A map of London** with markers for active road disruptions
- **4 metrics at the top**: Active Disruptions, Journeys Affected, Population Impacted, Camera Incidents
- **Coloured markers**: red = incident, orange = congested, yellow = slow, green = flowing
- **Click any marker** to see the camera thumbnail and impact numbers
- **Sidebar left**: click "Demo: Bank Station Closure" to see a hardcoded demo scenario
- **GPU vs CPU Benchmark** in the sidebar shows the speedup numbers

---

## Troubleshooting

### "Module not found: cudf"
```bash
pip install cudf-cu12 --extra-index-url=https://pypi.nvidia.com
```

### "Port 8501 already in use"
```bash
streamlit run main.py --server.port 8502
```
Then open `http://localhost:8502` in your browser (also update the SSH tunnel: `ssh -L 8502:localhost:8502 nvidia@hp-15.local`).

### "TfL API returns 0 disruptions"
This is normal — there may genuinely be no active road disruptions right now. Use the Demo button in the sidebar to see the system working.

### VLM fails with "CUDA out of memory"
The model loads in float16 and needs ~8GB of GPU VRAM. The DGX Spark has 128GB unified memory so this should not happen. If it does, try:
```bash
python3 -c "import torch; torch.cuda.empty_cache()"
```
Then restart the app.

### The app is loading for too long (>5 minutes)
The spatial join (bus stops → LSOA codes) runs once and caches to `data/stops_with_lsoa.parquet`. If it's stuck, wait it out — it only ever runs once.

### Can't connect to localhost:8501
Make sure you started the SSH session with port forwarding:
```powershell
ssh -L 8501:localhost:8501 nvidia@hp-15.local
```
Not just `ssh nvidia@hp-15.local`.

---

## Session Summary — What Each Terminal Does

| Terminal | Command | Purpose |
|---|---|---|
| Terminal 1 | `ssh -L 8501:localhost:8501 nvidia@hp-15.local` | Port-forwarded main session — run the app here |
| Browser | `http://localhost:8501` | View the Ripple UI |

The VLM model runs in-process inside the Streamlit app — no separate terminal needed.

---

## Quick Reference — Commands to Run in Order

```bash
# Terminal 1 (port-forwarded SSH)
ssh -L 8501:localhost:8501 nvidia@hp-15.local
cd ~/ripple
python3 scripts/download_data.py        # first time only
python3 scripts/download_road_network.py # first time only
streamlit run main.py --server.port 8501 --server.address 0.0.0.0

# Browser (Windows)
http://localhost:8501
```

# SPU Stormwater Reproduction Package

A self-contained snapshot of the work to pull, sample, and explore Seattle Public Utilities' (SPU) public stormwater asset inventory. Use this on a fresh machine to either (a) pick up where the original work left off using the included data, or (b) re-fetch from SPU's open APIs and rebuild from scratch.

## What's in here

```
spu/
├── README.md                 you are here
├── requirements.txt          Python dependencies
├── DATA_DICTIONARY.md        plain-language guide to the column schema
├── eda_v01.ipynb             starter Jupyter notebook for exploration
├── spu_bulk_fetch.py         pulls full feature records from SPU's REST API (~90 min)
├── spu_to_parquet.py         converts gzipped GeoJSON to Parquet
├── build_sample.py           builds the small EDA sample (~12 CSVs, 4 MB)
├── geojson/                  full feature data — 54 .geojson.gz files, ~260 MB
│                             (omit if using the starter package — re-run bulk fetch)
├── sample/                   12 CSVs + _index.csv covering the asset taxonomy (~4 MB)
├── spu_data/                 raw schema and count JSONs from the metadata fetches
└── parquet/                  empty — destination if/when you run spu_to_parquet.py
```

## Quick start (fresh machine)

Tested with macOS 14+ and Python 3.10–3.14. Adjust paths if your Desktop or working folder differs.

### 1. Place this folder

Unzip into your Desktop so the layout matches the scripts' default paths (`~/Desktop/spu/...`). If you put it somewhere else, edit the `IN_DIR` / `OUT_DIR` variables at the top of each `.py` file before running.

### 2. Create a virtual environment and install dependencies

```bash
cd ~/Desktop/spu
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Open the notebook

If you use VS Code, `code ~/Desktop/spu`, install the Python and Jupyter extensions if prompted, open `eda_v01.ipynb`, and select the `.venv` Python as the kernel. If you use plain Jupyter:

```bash
jupyter lab eda_v01.ipynb
```

The notebook loads the sample CSVs and adds geometry-derived `lat` / `lon` columns. It runs end-to-end without needing the full `geojson/` data.

## How the data was acquired

Three rounds of REST calls against SPU's ArcGIS Online services (org ID `ZOyb2t4B0UYuYNYH`):

1. **Service catalog** — one call to `https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services?f=json` to enumerate all 1,017 services Seattle hosts and identify the 17 SPU drainage/stormwater FeatureServers.

2. **Per-service metadata** — for each of the 17 services, one call each for:
   - `FeatureServer?f=json` — service-level info, layer list
   - `FeatureServer/0?f=json` — first sub-layer schema
   - `FeatureServer/0/query?where=1=1&returnCountOnly=true&f=json` — first sub-layer count

   Then a second pass for the 59 sub-layers across all 17 services (per-sub-layer schema + count).

   Output: the JSON files in `spu_data/`.

3. **Bulk feature fetch** — `spu_bulk_fetch.py` paginates each of the 59 sub-layers and writes one gzipped GeoJSON file per sub-layer. ~1,400 paginated requests, 60–90 minutes total. Output: the 54 non-empty files in `geojson/`.

To re-run from scratch on the new machine:

```bash
python3 spu_bulk_fetch.py    # 60–90 minutes; resumable
python3 build_sample.py      # ~1 minute; rebuilds the sample CSVs
python3 spu_to_parquet.py    # optional; converts geojson/ -> parquet/ (~5 min)
```

`spu_bulk_fetch.py` already has the full layer list and pagination logic baked in — no need to redo the metadata rounds unless SPU's catalog changes.

## Notes for a corporate / work-computer environment

- **Network policy**: the bulk fetch hits `services.arcgis.com` over HTTPS. SPU's servers are public and not flagged on most corporate proxies, but verify before running. If SSL verification fails (corporate certificate inspection, etc.), the fetch script already disables verification — see the `SSL_CTX` line.
- **Python version**: most data libraries (pandas, geopandas, shapely) work best on stable Python 3.11 or 3.12. If your work machine has only 3.14 (very recent), some packages may need a wheel build; downgrade to 3.12 if you hit binary-package install errors.
- **Pip + corporate proxies**: if `pip install` fails, try adding `--trusted-host pypi.org --trusted-host files.pythonhosted.org` to bypass strict TLS-inspection setups.

## Source data

All assets in `geojson/` are derived from SPU's public ArcGIS Online services (org `ZOyb2t4B0UYuYNYH`). Original data is owned and maintained by Seattle Public Utilities — Drainage and Wastewater. Refer to [Seattle GeoData](https://data-seattlecitygis.opendata.arcgis.com) for the canonical hub.

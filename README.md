# SPU Stormwater Asset Data: A Guide to What Was Built and How

A worked example of collecting a real utility's stormwater asset inventory from public sources, turning it into analysis-ready files, and publishing an interactive map.

The example utility is **Seattle Public Utilities (SPU)**. The method applies to any owner that publishes its assets through ArcGIS services.

> **How to read this guide.**
> Everyone: read sections 1 to 3 and the glossary (section 11).
> Engineers: start at section 4, then use sections 5 to 10 as reference.

---

## 1. What this is (plain language)

Cities own huge networks of pipes, drains, pumps, ponds, and rain gardens that carry rainwater away and reduce flooding. Few owners can say, in one place, exactly what they have and where it is.

This project took one utility that publishes its inventory openly, Seattle Public Utilities, and did four things:

1. **Collected** every public stormwater and drainage layer SPU offers (about 2.8 million records).
2. **Organized** the records into small, easy-to-open sample files and a plain-language data dictionary.
3. **Explored** them in notebooks.
4. **Published** an interactive map of a downtown Seattle slice (Pioneer Square, SODO, Elliott Bay).

The purpose was to prove that a realistic, complete asset inventory can be collected quickly. It is the data foundation for a prototype AI tool that would let infrastructure owners ask questions across their own data.

## 2. At a glance

| | |
|---|---|
| **Source** | SPU's public ArcGIS Online services, also listed on [Seattle GeoData](https://data-seattlecitygis.opendata.arcgis.com) |
| **Snapshot date** | April 28, 2026 (the fetch took about 82 minutes) |
| **Scope** | 17 FeatureServers, 59 sub-layers; 54 contained records, 5 were empty; 0 errors |
| **Size** | 2,817,689 features in 54 gzipped GeoJSON files (about 254 MB compressed) |
| **Format** | GeoJSON (WGS84 lat/lon), plus CSV samples with geometry stored as text (WKT) |
| **Public demo** | Live at https://chriseshleman.github.io/spu-stormwater-map/ (one `index.html` hosted on GitHub Pages; see the basemap note in section 8) |
| **Skills needed to rebuild** | Basic Python and a terminal. No database or paid software. |

The 2,817,689 total counts every lifecycle state (active, proposed, abandoned, removed). An earlier project note cited about 2.75 million *active* features; that figure was not re-derived here.

## 3. What is in the data

SPU names its layers `SPU_DWW_*` ("DWW" is the Drainage and Wastewater division). The table maps them to the standard asset categories used in this work.

| Category | SPU layer family | Features |
|---|---|---:|
| Conveyance | Non-Mainline Points (structures tied to non-mainline pipes, such as wyes and downspouts) | 2,042,539 |
| Conveyance | Mainline Points (end points) | 399,453 |
| Conveyance | Mainlines (the pipes) | 136,669 |
| Conveyance | Curb and Gutter | 33,887 |
| Conveyance | Ditches and Culverts | 26,741 |
| Collection and inlets | Catch Basins, Junction Boxes, Sandboxes, Trash Racks | 98,018 |
| Collection and inlets | Surface Drainage Points | 15,411 |
| Green infrastructure | Green Stormwater Infrastructure (swales, rain gardens, permeable pavement, and others) | 56,168 |
| Treatment | Water Quality Structures | 3,717 |
| Outfalls | Storm Outfalls | 2,472 |
| Detention | Miscellaneous Structures (pump station, vault, and detention footprints) | 1,559 |
| Detention | Vaults / Ponds / Underground Injection Cells | 364 / 53 / 32 |
| Pump stations | Pump Stations | 141 |
| Service areas | CSO Basins (combined sewer overflow areas) | 81 |
| Other | Appurtenance Valves | 384 |
| Flood barriers | None found in SPU's public layers | 0 |

Counts come from reading the 54 files in `geojson/`.

## 4. How it was built (the pipeline)

```
SPU ArcGIS REST API
   -> spu_bulk_fetch.py        -> geojson/  (54 .geojson.gz, full data)
        -> build_sample.py     -> sample/      (random sample, about 4 MB)
        -> build_geo_sample.py -> sample_geo/  (all features inside a map area, about 6 MB)
        -> spu_to_parquet.py   -> parquet/     (optional, columnar copy)
   sample/, sample_geo/ -> eda_v01.ipynb (exploration), map_v2.html (map)
   sample_geo/ -> generate_public_map.py -> spu-stormwater-map/index.html -> GitHub Pages
```

1. **Find the services.** One call to `https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services?f=json` listed 1,017 services hosted by the City of Seattle (org ID `ZOyb2t4B0UYuYNYH`). Of those, 17 FeatureServers are SPU drainage and stormwater services.
2. **Read the metadata.** For each service, and then each of the 59 sub-layers, a call fetched the schema and the record count. The results are in `spu_data/`. This step shows what a layer contains before downloading it.
3. **Bulk fetch.** `spu_bulk_fetch.py` pages through each sub-layer 2,000 records at a time (about 1,400 requests) and writes one compressed GeoJSON file per sub-layer. It is resumable and skips files that already exist.
4. **Make samples.** The full data is too big for quick exploration, so two small versions are built:
   - `sample/`: a random sample per layer (fixed seed 42, so reproducible from the same input). The `_index.csv` file records how large each sample is compared with the full layer.
   - `sample_geo/`: every feature that falls inside a bounding box, so layers line up on a map.
5. **Explore.** `eda_v01.ipynb` loads the samples and adds latitude and longitude columns.
6. **Publish.** `generate_public_map.py` draws the `sample_geo/` layers on one folium map with toggles, a legend, and a title banner. The single HTML file is committed to a separate repo for GitHub Pages.

## 5. Quick start (engineers)

Tested on macOS with Python 3.10 to 3.14. Python 3.11 or 3.12 gives the smoothest installs for the geospatial libraries.

```bash
# 1. Get the code. The scripts expect the folder at ~/Desktop/spu (see section 9)
git clone https://github.com/chriseshleman/spu-stormwater.git ~/Desktop/spu
cd ~/Desktop/spu

# 2. Environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Path A: use what is included (about 5 minutes).** `sample/`, `sample_geo/`, and `spu_data/` are committed, so skip the download.

```bash
jupyter lab eda_v01.ipynb          # or open it in VS Code and select the .venv kernel
```

**Path B: rebuild from scratch (about 90 minutes).** The full `geojson/` folder is not in git.

```bash
python3 spu_bulk_fetch.py     # 60 to 90 minutes; resumable
python3 build_sample.py       # about 1 minute
python3 build_geo_sample.py   # about 1 minute
python3 spu_to_parquet.py     # optional, about 5 minutes
```

Re-running the fetch pulls SPU's current data, so counts will differ from the April 28, 2026 snapshot.

## 6. File reference

| Path | What it is |
|---|---|
| `README.md` | This guide |
| `DATA_DICTIONARY.md` | Plain-language guide to column names and SPU's prefix codes (`OUT_` outfalls, `MNL_` mainlines, `PS_` pump stations, `CB_` catch basins, `DCH_` ditches and culverts, `CSOB_` CSO basins, `BSL_` bioswales) |
| `requirements.txt` | Python dependencies (pandas, numpy, shapely, geopandas, pyogrio, pyproj, folium, ipykernel, pyarrow) |
| `spu_bulk_fetch.py` | Downloads every sub-layer to `geojson/`. Standard library only |
| `build_sample.py` | Random sample CSVs plus `_index.csv` |
| `build_geo_sample.py` | Bounding-box CSVs. The box is set in `BBOX` near the top |
| `spu_to_parquet.py` | Converts the GeoJSON files to Parquet |
| `generate_public_map.py` | Builds the public map page |
| `eda_v01.ipynb`, `eda_vB01.ipynb` | Exploration notebooks (the second is about 22 MB because outputs are saved) |
| `map.html`, `map_v2.html` | Earlier folium maps (6 MB and 20 MB) |
| `spu_data/` | Schemas, counts, and metadata JSON from the API |
| `sample/`, `sample_geo/` | CSV samples |
| `geojson/` | Full data (git-ignored) |
| `parquet/` | Empty until you run the conversion (git-ignored) |

## 7. Working with the data

Full data (GeoJSON):

```python
import gzip, json
with gzip.open("geojson/SPU_DWW_Storm_Outfalls__0.geojson.gz", "rt") as f:
    fc = json.load(f)              # a FeatureCollection
print(len(fc["features"]))         # 2472
print(fc["features"][0]["properties"].keys())
```

Samples (CSV with geometry as text):

```python
import pandas as pd
from shapely import from_wkt
df = pd.read_csv("sample/SPU_DWW_Storm_Outfalls__0.csv", low_memory=False)
df["geometry"] = df["geometry_wkt"].apply(from_wkt)
```

Useful column patterns (full list in `DATA_DICTIONARY.md`):

- `*_LIFECYCLE_CODE` tells whether an asset is current, proposed, or retired. Filter on it, because the counts above include every state.
- `*_OWNER_NAME` shows who owns the asset. Many side sewers are private even though SPU tracks them.
- `*_NPDES_ID` is the federal discharge permit ID, mainly on outfalls.
- Coordinate columns inside the data are patchy. Use the `lat` and `lon` columns the notebook adds, or the geometry itself.

## 8. The public map

- **Live page:** https://chriseshleman.github.io/spu-stormwater-map/, served by GitHub Pages from the repo `github.com/chriseshleman/spu-stormwater-map`. That repo holds only the output: one `index.html` (about 25.5 MB) and a README. The code that builds it lives in this repo.
- **Contents:** about 18,000 features across 23 asset classes for the downtown bounding box, with a legend and per-layer toggles.
- **Basemap warning.** The map draws its background tiles from Carto ("Positron"). Carto now requires an API key for those tiles, so the page shows "api key required" stripes across the background. The asset layers still load and work. `map.html` and `map_v2.html` use the same tiles and show the same stripes.
  - **Fix:** in `generate_public_map.py`, change `tiles="cartodbpositron"` to `tiles="OpenStreetMap"`, which needs no key. Regenerate the map and replace `index.html` in the map repo. A lighter gray look needs a keyed provider, such as the free tiers at Carto, Stadia, or MapTiler.
- **To regenerate:** run `build_geo_sample.py`, then `generate_public_map.py`, then copy or commit the resulting `index.html` into the map repo.
- **To host your own copy:** create a repo for the output, commit `index.html`, then turn on Pages under the repo's Settings.

## 9. Known issues and gotchas

1. **Basemap stripes.** See section 8. The fix is one line in `generate_public_map.py`.
2. **Hard-coded paths.** Every script assumes the project sits at `~/Desktop/spu`. Elsewhere, edit `IN_DIR`, `OUT_DIR`, and `ROOT` at the top of each script. `generate_public_map.py` also writes to `~/Desktop/spu-stormwater-map/index.html`.
3. **Map script docstring is out of date.** It says the output goes to `docs/index.html`, but the code writes to the separate map folder.
4. **Changing the map area takes two edits.** `build_geo_sample.py` holds `BBOX`. `generate_public_map.py` has the map center typed in separately (`BBOX_CENTER`), so update both.
5. **Where the map code lives.** `generate_public_map.py` belongs to this repo. The map repo holds only its output, and its README points back here for regeneration.
6. **Data moves.** SPU refreshes its layers, so a re-fetch will not match the snapshot. Counts and lifecycle states change over time.
7. **SSL verification is off in the fetch script.** It was done to work behind corporate proxies, and SPU's server is public data. Turn verification back on (remove the `SSL_CTX` override) if your environment allows.
8. **A layer rename would break the fetch.** The layer list is baked into `spu_bulk_fetch.py`. Re-run the metadata step if SPU's catalog changes.
9. **Flood barriers are absent.** SPU's public layers have no levees, floodwalls, or tide gates, which matters for owners with coastal exposure.

## 10. Why Seattle, and how to repeat this elsewhere

Seattle was chosen because it publishes a near-complete drainage inventory in a standard ArcGIS format with public, queryable services. Among the owners checked, Philadelphia published inlets, outfalls, and green infrastructure but no pipe or pump-station layers were found. Washington, DC publishes outfalls and sewersheds, but its pipe network is not public.

To repeat the method for another owner:

1. Find the owner's ArcGIS organization ID (look in the REST service URLs behind its open-data map).
2. List its services (`.../rest/services?f=json`) and pick the drainage and stormwater ones.
3. Fetch the schema and record count for each sub-layer.
4. Adapt `spu_bulk_fetch.py` with the new base URL and layer list.

## 11. Glossary

| Term | Meaning |
|---|---|
| **Asset** | One physical thing the owner maintains: a pipe, catch basin, outfall, pump, or pond |
| **Catch basin** | A street drain with a sump that traps debris before water enters the pipe |
| **CSO** | Combined sewer overflow: when a combined sewer system overflows to a waterway in heavy rain |
| **DWW** | Drainage and Wastewater, SPU's division |
| **FeatureServer** | An ArcGIS web service that serves map records through a standard web address |
| **GeoJSON** | A text format for map features (a shape plus its attributes) |
| **GSI** | Green stormwater infrastructure: rain gardens, bioswales, permeable pavement, and similar |
| **Mainline** | A main pipe in the network, as opposed to a small connecting line |
| **MS4** | Municipal separate storm sewer system, the permit category for a city's stormwater network |
| **NPDES** | National Pollutant Discharge Elimination System, the federal permit program |
| **Outfall** | The point where the drainage system discharges to a creek, lake, or bay |
| **Parquet** | A compact column-based file format, faster than CSV for big tables |
| **Sub-layer** | One table inside a service, such as the outfalls layer within a larger service |
| **WKT** | Well-known text, a plain-text way to write a shape, for example `POINT (-122.27 47.66)` |

## 12. Source and attribution

All data is owned and maintained by Seattle Public Utilities, Drainage and Wastewater. The canonical hub is [Seattle GeoData](https://data-seattlecitygis.opendata.arcgis.com). Check the City of Seattle's terms of use before redistributing the data, particularly the full `geojson/` files, which are intentionally not included in git. SPU's data is provided without guarantees of accuracy or completeness.

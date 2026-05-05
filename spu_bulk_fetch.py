#!/usr/bin/env python3
"""
SPU Stormwater bulk fetch — paginated GeoJSON, one gzipped file per sub-layer.

Stdlib only. Run on macOS with the system Python 3.

Output: ~/Desktop/spu/geojson/  (created if needed)
        59 files of the form <service>__<layer-id>.geojson.gz
        plus a manifest.json describing what was pulled.

Resumable: skips any file already present.
"""
import json
import gzip
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# macOS Python often lacks CA bundle access; SPU is public open data, so
# verification is not a security concern here.
SSL_CTX = ssl._create_unverified_context()

OUT_DIR = os.path.expanduser("~/Desktop/spu/geojson")
BASE = "https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services"
PAGE = 2000        # ArcGIS default max records per request
SR = 4326          # WGS84 lat/lon
TIMEOUT = 90       # seconds per request
RETRIES = 4        # retries per page on transient errors
SLEEP_OK = 0.10    # polite throttle between successful pages
SLEEP_RETRY = 6    # backoff between retries

# (service, sub_layer_id, friendly_name, expected_count)
LAYERS = [
    ("DWW_Pump_Stationsss", 0, "DWW Pump Stations Internal", 141),
    ("SPU_DWW_Appurtenance_Valves", 0, "DWW Appurtenance Points", 384),
    ("SPU_DWW_CSO_Basins_", 0, "SPU DWW CSO Basins Internal", 81),
    ("SPU_DWW_Catch_Basins_Junction_Boxes_Sandboxes_DSO_External", 2, "Catch Basins", 91965),
    ("SPU_DWW_Catch_Basins_Junction_Boxes_Sandboxes_DSO_External", 4, "Sandboxes and Junction Boxes", 6054),
    ("SPU_DWW_Ditches_and_Culverts_DSO_EXT_View", 1, "SPU DWW Ditches and Culverts", 26741),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 2, "SPU DWW GSI Weirs", 169),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 3, "SPU DWW Swales", 12743),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 4, "SPU DWW Underdrains & Rain Gardens", 14004),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 5, "SPU DWW Permeable Pavement", 4103),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 6, "SPU DWW GSI Facility Footprints", 23969),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 7, "SPU DWW Other GSI Footprints", 555),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 9, "SPU DWW Proposed GSI Weirs", 0),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 10, "SPU DWW Proposed Swales", 146),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 11, "SPU DWW Proposed Underdrains & Rain Gardens", 177),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 12, "SPU DWW Proposed Permeable Pavement", 70),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 13, "SPU DWW Proposed GSI Facility Footprints", 169),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 14, "SPU DWW Proposed Other GSI Footprints", 25),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 16, "SPU DWW Aba Rem GSI Weirs", 0),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 17, "SPU DWW Aba Rem Swales", 9),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 18, "SPU DWW Aba Rem Permeable Pavement", 0),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 19, "SPU DWW Aba Rem Underdrains & Rain Gardens", 19),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 20, "SPU DWW Aba Rem Facility Footprints", 10),
    ("SPU_DWW_Green_Stormwater_Infrastructure", 21, "SPU DWW Aba Rem Other GSI Footprints", 0),
    ("SPU_DWW_Mainline_Points_External", 1, "SPU DWW Mainline End Points", 66157),
    ("SPU_DWW_Mainline_Points_External", 2, "SPU DWW Proposed Mainline End Points", 618),
    ("SPU_DWW_Mainline_Points_External", 3, "SPU DWW Aba Rem Mainline End Points", 4493),
    ("SPU_DWW_Mainline_Points_External", 4, "SPU DWW Force Mainline End Points", 416),
    ("SPU_DWW_Mainline_Points_External", 5, "DWW Mainline Connection Points Wyes", 327770),
    ("SPU_DWW_Mainlines_External", 8, "SPU DWW Mainline Detention Polygons", 275),
    ("SPU_DWW_Mainlines_External", 10, "SPU DWW Mainlines (Permitted Use)", 65234),
    ("SPU_DWW_Mainlines_External", 11, "SPU DWW Mainlines (Probable Flow)", 65234),
    ("SPU_DWW_Mainlines_External", 12, "SPU DWW Proposed Mainline Pipes", 640),
    ("SPU_DWW_Mainlines_External", 13, "SPU DWW Aba Rem Mainlines", 4390),
    ("SPU_DWW_Mainlines_External", 14, "SPU DWW Force Mainlines", 520),
    ("SPU_DWW_Mainlines_External", 15, "SPU DWW Mainline Detention Lines", 376),
    ("SPU_DWW_Miscellaneous_Structures", 1, "Misc Structure Polygons", 1264),
    ("SPU_DWW_Miscellaneous_Structures", 2, "Proposed Polygons", 95),
    ("SPU_DWW_Miscellaneous_Structures", 3, "Aba Rem Polygons", 200),
    ("SPU_DWW_Non_Mainlines_External_DSO_view", 1, "SPU Owned Non-Mainlines", 94263),
    ("SPU_DWW_Non_Mainlines_External_DSO_view", 2, "Non-SPU Owned Non-Mainlines", 1928366),
    ("SPU_DWW_Non_Mainlines_External_DSO_view", 3, "Non-Mainline Detention Lines", 6322),
    ("SPU_DWW_Non_Mainlines_External_DSO_view", 4, "Non-Mainline Detention Polygons", 13590),
    ("SPU_DWW_Ponds", 0, "SPU DWW Ponds Internal", 53),
    ("SPU_DWW_Storm_Outfalls", 0, "SPU DWW Storm Outfalls Internal", 2472),
    ("SPU_DWW_Surface_Drainage_Curb_and_Gutter", 1, "Surface Drainage Curb and Gutter", 33887),
    ("SPU_DWW_Surface_Drainage_Curb_and_Gutter", 2, "Aba Rem Surface Drainage Curb and Gutter", 375),
    ("SPU_DWW_Surface_Drainage_Points", 1, "Surface Drainage Points", 15112),
    ("SPU_DWW_Surface_Drainage_Points", 2, "Proposed Surface Drainage Points", 183),
    ("SPU_DWW_Surface_Drainage_Points", 3, "Aba Rem Surface Drainage Points", 116),
    ("SPU_DWW_Underground_Injection_Cells", 1, "Surface Drainage Points", 32),
    ("SPU_DWW_Underground_Injection_Cells", 2, "Proposed Surface Drainage Points", 0),
    ("SPU_DWW_Vaults", 0, "SPU DWW Vaults Internal", 364),
    ("SPU_DWW_Water_Quality_Structures", 1, "DWW Water Quality Points", 1838),
    ("SPU_DWW_Water_Quality_Structures", 2, "DWW WQS Polygons", 1581),
    ("SPU_DWW_Water_Quality_Structures", 4, "DWW Proposed Water Quality Points", 102),
    ("SPU_DWW_Water_Quality_Structures", 5, "DWW Proposed WQS Polygons", 102),
    ("SPU_DWW_Water_Quality_Structures", 7, "DWW Aba Rem Water Quality Points", 73),
    ("SPU_DWW_Water_Quality_Structures", 8, "DWW Aba Rem WQS Polygons", 21),
]


def http_get_json(url):
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "spu-bulk-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            last_err = e
            sys.stdout.write(f"      retry {attempt}/{RETRIES} after error: {e}\n")
            sys.stdout.flush()
            time.sleep(SLEEP_RETRY * attempt)
    raise RuntimeError(f"Failed after {RETRIES} retries: {last_err}")


def fetch_layer(service, lid, name, expected):
    out_path = os.path.join(OUT_DIR, f"{service}__{lid}.geojson.gz")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"  [skip — already done] {os.path.basename(out_path)}")
        return os.path.getsize(out_path)

    if expected == 0:
        print(f"  [skip — empty layer] {name}")
        return 0

    print(f"  Fetching: {name}  ({service}/{lid})  expected={expected:,}")
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": SR,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "returnGeometry": "true",
        }
        url = f"{BASE}/{service}/FeatureServer/{lid}/query?" + urllib.parse.urlencode(params)
        data = http_get_json(url)
        feats = data.get("features", [])
        features.extend(feats)
        sys.stdout.write(f"    page offset={offset:>9,}  got={len(feats):>5}  total={len(features):>9,}\r")
        sys.stdout.flush()
        if len(feats) < PAGE:
            break
        offset += PAGE
        time.sleep(SLEEP_OK)
    print()  # newline after the carriage-return progress

    fc = {"type": "FeatureCollection", "features": features}
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump(fc, f, separators=(",", ":"))
    sz = os.path.getsize(out_path)
    print(f"    -> wrote {len(features):,} features ({sz:,} bytes gz)")
    if expected and abs(len(features) - expected) > 5:
        print(f"    !! WARNING: expected ~{expected:,} got {len(features):,}")
    return sz


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Output dir: {OUT_DIR}")
    print(f"Layers to fetch: {len(LAYERS)}")
    print()
    started = time.time()
    total_bytes = 0
    fetched_layers = 0
    errors = []
    for i, (s, lid, name, exp) in enumerate(LAYERS, 1):
        print(f"[{i:>2}/{len(LAYERS)}] {s} / {lid}")
        try:
            total_bytes += fetch_layer(s, lid, name, exp)
            fetched_layers += 1
        except Exception as e:
            print(f"    !! ERROR: {e}")
            errors.append((s, lid, str(e)))
    dur = time.time() - started

    # Manifest
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(dur, 1),
        "out_sr": SR,
        "page_size": PAGE,
        "layers_attempted": len(LAYERS),
        "layers_succeeded": fetched_layers,
        "errors": [{"service": s, "layer": l, "error": e} for s, l, e in errors],
        "files": sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".geojson.gz")),
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print()
    print("=" * 60)
    print(f"DONE in {dur/60:.1f} minutes")
    print(f"  Layers OK: {fetched_layers}/{len(LAYERS)}")
    print(f"  Errors:    {len(errors)}")
    print(f"  Total gz:  {total_bytes/1e6:.1f} MB")
    print(f"  Output:    {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""Build a geographically-constrained sample for visualization.

Filters every full GeoJSON layer to features whose geometry intersects
a target bounding box, then writes one CSV per layer to ~/Desktop/spu/sample_geo/.

Unlike the random sample (sample/), this preserves spatial continuity —
every asset of every type within the chosen neighborhood is kept. The
result is a dense, realistic slice you can map without artifacts.

Edit BBOX below to change the geographic area.
"""
import csv
import gzip
import json
import time
from pathlib import Path

# ----------------------------------------------------------------------------
# Bounding box in WGS84 lat/lon (decimal degrees)
# Default: ~Pioneer Square -> SODO -> Beacon Hill west edge -> Elliott Bay
# ~3.3 km E-W x 3.0 km N-S
# ----------------------------------------------------------------------------
BBOX = {
    "min_lat": 47.575,
    "max_lat": 47.610,
    "min_lon": -122.350,
    "max_lon": -122.315,
    "name": "Pioneer Square / SODO / Elliott Bay waterfront",
}

IN_DIR = Path.home() / "Desktop" / "spu" / "geojson"
OUT_DIR = Path.home() / "Desktop" / "spu" / "sample_geo"

# Friendly label + taxonomy class for each layer file
# (extends what was in the random sample's _index.csv to all layers)
LABELS = {
    "DWW_Pump_Stationsss__0": ("Pump Stations", "Pump Stations"),
    "SPU_DWW_Appurtenance_Valves__0": ("Appurtenance Valves", "Appurtenances"),
    "SPU_DWW_CSO_Basins___0": ("CSO Basins", "Service Areas"),
    "SPU_DWW_Catch_Basins_Junction_Boxes_Sandboxes_DSO_External__2": ("Catch Basins", "Collection"),
    "SPU_DWW_Catch_Basins_Junction_Boxes_Sandboxes_DSO_External__4": ("Sandboxes & Junction Boxes", "Collection"),
    "SPU_DWW_Ditches_and_Culverts_DSO_EXT_View__1": ("Ditches & Culverts", "Conveyance"),
    "SPU_DWW_Green_Stormwater_Infrastructure__2": ("GSI Weirs", "Green Infrastructure"),
    "SPU_DWW_Green_Stormwater_Infrastructure__3": ("GSI Swales", "Green Infrastructure"),
    "SPU_DWW_Green_Stormwater_Infrastructure__4": ("GSI Underdrains & Rain Gardens", "Green Infrastructure"),
    "SPU_DWW_Green_Stormwater_Infrastructure__5": ("GSI Permeable Pavement", "Green Infrastructure"),
    "SPU_DWW_Green_Stormwater_Infrastructure__6": ("GSI Facility Footprints", "Green Infrastructure"),
    "SPU_DWW_Green_Stormwater_Infrastructure__7": ("Other GSI Footprints", "Green Infrastructure"),
    "SPU_DWW_Mainline_Points_External__1": ("Mainline End Points", "Conveyance"),
    # Wyes (327K) are connection points between laterals and mains —
    # dense, visually noisy, not a primary visualization layer. Skipped.
    # "SPU_DWW_Mainline_Points_External__5": ("Mainline Connection Points (Wyes)", "Conveyance"),
    "SPU_DWW_Mainlines_External__10": ("Mainlines (Permitted Use)", "Conveyance"),
    "SPU_DWW_Mainlines_External__14": ("Force Mainlines", "Conveyance"),
    "SPU_DWW_Miscellaneous_Structures__1": ("Misc Structures", "Misc"),
    "SPU_DWW_Non_Mainlines_External_DSO_view__1": ("SPU-Owned Non-Mainlines", "Conveyance"),
    # Private laterals (1.93M features, 180 MB) excluded from geo sample —
    # would visually swamp the map and add little signal beyond density.
    # "SPU_DWW_Non_Mainlines_External_DSO_view__2": ("Private Non-Mainlines (Laterals)", "Conveyance"),
    "SPU_DWW_Ponds__0": ("Ponds", "Detention"),
    "SPU_DWW_Storm_Outfalls__0": ("Storm Outfalls", "Outfalls"),
    "SPU_DWW_Surface_Drainage_Curb_and_Gutter__1": ("Curb & Gutter", "Conveyance"),
    "SPU_DWW_Surface_Drainage_Points__1": ("Surface Drainage Points", "Conveyance"),
    "SPU_DWW_Underground_Injection_Cells__1": ("Underground Injection Cells", "Detention"),
    "SPU_DWW_Vaults__0": ("Vaults", "Detention"),
    "SPU_DWW_Water_Quality_Structures__1": ("Water Quality Points", "Treatment"),
    "SPU_DWW_Water_Quality_Structures__2": ("Water Quality Polygons", "Treatment"),
}


# ---------------- Geometry helpers (no shapely needed) ----------------------

def gj_to_wkt(g):
    if g is None: return None
    t = g.get("type"); c = g.get("coordinates")
    if c is None: return None
    fmt = lambda p: f"{p[0]} {p[1]}"
    ring = lambda r: "(" + ", ".join(fmt(p) for p in r) + ")"
    try:
        if t == "Point":           return f"POINT ({fmt(c)})"
        if t == "MultiPoint":      return "MULTIPOINT (" + ", ".join(fmt(p) for p in c) + ")"
        if t == "LineString":      return "LINESTRING (" + ", ".join(fmt(p) for p in c) + ")"
        if t == "MultiLineString": return "MULTILINESTRING (" + ", ".join(ring(L) for L in c) + ")"
        if t == "Polygon":         return "POLYGON (" + ", ".join(ring(r) for r in c) + ")"
        if t == "MultiPolygon":    return "MULTIPOLYGON (" + ", ".join("(" + ", ".join(ring(r) for r in poly) + ")" for poly in c) + ")"
    except Exception:
        return None
    return None


def geom_bbox(g):
    """Return (minx, miny, maxx, maxy) for any GeoJSON geometry, or None."""
    if g is None or g.get("coordinates") is None:
        return None
    xs, ys = [], []
    def walk(c):
        if isinstance(c, (list, tuple)):
            if c and isinstance(c[0], (int, float)):
                xs.append(c[0]); ys.append(c[1])
            else:
                for sub in c:
                    walk(sub)
    walk(g["coordinates"])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_intersects(geom_bb, target_bb):
    if geom_bb is None:
        return False
    return not (
        geom_bb[2] < target_bb[0] or geom_bb[0] > target_bb[2] or
        geom_bb[3] < target_bb[1] or geom_bb[1] > target_bb[3]
    )


# ---------------- Main --------------------------------------------------------

def main():
    target = (BBOX["min_lon"], BBOX["min_lat"], BBOX["max_lon"], BBOX["max_lat"])
    OUT_DIR.mkdir(exist_ok=True)
    files = sorted(IN_DIR.glob("*.geojson.gz"))

    print(f"Filtering to bounding box: {BBOX['name']}")
    print(f"  lat {BBOX['min_lat']} to {BBOX['max_lat']}, "
          f"lon {BBOX['min_lon']} to {BBOX['max_lon']}")
    print(f"Input dir:  {IN_DIR}")
    print(f"Output dir: {OUT_DIR}\n")

    index_rows = []
    total_kept = 0
    started = time.time()

    for p in files:
        stem = p.name.replace(".geojson.gz", "")
        if stem not in LABELS:
            print(f"  [skip — no label] {p.name}")
            continue

        label, asset_class = LABELS[stem]
        out_name = stem + ".csv"
        out_path = OUT_DIR / out_name
        # Resume: skip already-processed layers
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"  [skip — already done] {label}")
            continue
        t0 = time.time()
        with gzip.open(p, "rt", encoding="utf-8") as f:
            fc = json.load(f)
        feats = fc.get("features", [])
        n_total = len(feats)

        kept = []
        for ft in feats:
            if bbox_intersects(geom_bbox(ft.get("geometry")), target):
                kept.append(ft)
        n_kept = len(kept)

        if n_kept == 0:
            print(f"  {label:<35} {0:>5,}/{n_total:<7,} (none in bbox)")
            continue

        rows, fields = [], set()
        for ft in kept:
            row = dict(ft.get("properties") or {})
            row["geometry_wkt"] = gj_to_wkt(ft.get("geometry"))
            row["geometry_type"] = (ft.get("geometry") or {}).get("type")
            rows.append(row)
            fields.update(row.keys())

        cols_priority = ["geometry_type", "geometry_wkt"]
        cols = sorted(c for c in fields if c not in cols_priority) + cols_priority

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

        elapsed = time.time() - t0
        sz = out_path.stat().st_size / 1024
        print(f"  {label:<35} {n_kept:>5,}/{n_total:<7,}  ->  {out_name}  ({sz:.0f} KB, {elapsed:.1f}s)")

        index_rows.append({
            "file": out_name,
            "label": label,
            "asset_class": asset_class,
            "geometry_type": rows[0]["geometry_type"],
            "n_features_in_geo_sample": n_kept,
            "n_features_in_full": n_total,
            "n_attributes": len(cols) - 2,
        })
        total_kept += n_kept

    # Build index from all CSVs that exist in OUT_DIR (handles resume cleanly)
    all_index = []
    for csv_path in sorted(OUT_DIR.glob("*.csv")):
        stem = csv_path.stem
        if stem.startswith("_"): continue
        if stem not in LABELS: continue
        label, asset_class = LABELS[stem]
        # Read just to count rows + grab geom type
        with open(csv_path, encoding="utf-8") as f:
            r = csv.DictReader(f)
            geom_type = ""
            n = 0
            for row in r:
                if not geom_type:
                    geom_type = row.get("geometry_type", "")
                n += 1
        # Cross-reference n_features_in_full from in-memory index_rows if available
        full_count = next((row["n_features_in_full"] for row in index_rows if row["file"] == csv_path.name), "")
        all_index.append({
            "file": csv_path.name,
            "label": label,
            "asset_class": asset_class,
            "geometry_type": geom_type,
            "n_features_in_geo_sample": n,
            "n_features_in_full": full_count,
            "n_attributes": len(r.fieldnames) - 2 if r.fieldnames else 0,
        })

    geo_order = {"Polygon": 0, "MultiPolygon": 0, "LineString": 1, "MultiLineString": 1, "Point": 2}
    all_index.sort(key=lambda r: (geo_order.get(r["geometry_type"], 9), -r["n_features_in_geo_sample"]))

    if all_index:
        with open(OUT_DIR / "_index.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_index[0].keys()))
            w.writeheader()
            w.writerows(all_index)

    # Manifest
    with open(OUT_DIR / "manifest.json", "w") as f:
        json.dump({
            "bbox": BBOX,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_seconds": round(time.time() - started, 1),
            "layers": len(index_rows),
            "total_features": total_kept,
        }, f, indent=2)

    print(f"\n{'-'*60}")
    print(f"DONE in {time.time() - started:.0f}s")
    print(f"  Layers with features in bbox: {len(index_rows)}")
    print(f"  Total features:               {total_kept:,}")
    print(f"  Output:                       {OUT_DIR}")


if __name__ == "__main__":
    main()

"""Build a small EDA-friendly sample from ~/Desktop/spu/geojson/.

Output: ~/Desktop/spu/sample/<layer>.csv  (one CSV per sub-layer)
        ~/Desktop/spu/sample/_index.csv   (manifest of what's in the sample)

Each CSV row = one feature, with all original attributes plus
`geometry_wkt` (Well-Known Text) and `geometry_type`.  WKT is the
universal portable geometry format — pandas reads it as a string;
shapely / geopandas can parse it back into geometries when needed.
"""
import csv
import gzip
import json
import random
from pathlib import Path

random.seed(42)

IN_DIR = Path.home() / "Desktop" / "spu" / "geojson"
OUT_DIR = Path.home() / "Desktop" / "spu" / "sample"
OUT_DIR.mkdir(exist_ok=True)

# (filename in geojson/, sample size or None for all, friendly label, asset class)
PICKS = [
    ("SPU_DWW_Storm_Outfalls__0.geojson.gz",                                      None,  "Storm Outfalls",            "Outfalls"),
    ("DWW_Pump_Stationsss__0.geojson.gz",                                         None,  "Pump Stations",             "Pump Stations"),
    ("SPU_DWW_CSO_Basins___0.geojson.gz",                                         None,  "CSO Basins",                "Service Areas"),
    ("SPU_DWW_Ponds__0.geojson.gz",                                               None,  "Ponds",                     "Detention"),
    ("SPU_DWW_Vaults__0.geojson.gz",                                              None,  "Vaults",                    "Detention"),
    ("SPU_DWW_Green_Stormwater_Infrastructure__2.geojson.gz",                     None,  "GSI Weirs",                 "Green Infrastructure"),
    ("SPU_DWW_Green_Stormwater_Infrastructure__3.geojson.gz",                     1000,  "GSI Swales (sample)",       "Green Infrastructure"),
    ("SPU_DWW_Underground_Injection_Cells__1.geojson.gz",                         None,  "Underground Injection Cells","Detention"),
    ("SPU_DWW_Appurtenance_Valves__0.geojson.gz",                                 None,  "Appurtenance Valves",       "Appurtenances"),
    ("SPU_DWW_Catch_Basins_Junction_Boxes_Sandboxes_DSO_External__2.geojson.gz",  1500,  "Catch Basins (sample)",     "Collection"),
    ("SPU_DWW_Mainlines_External__10.geojson.gz",                                 1500,  "Mainlines Permitted Use (sample)", "Conveyance"),
    ("SPU_DWW_Ditches_and_Culverts_DSO_EXT_View__1.geojson.gz",                   1000,  "Ditches & Culverts (sample)",      "Conveyance"),
]


def gj_to_wkt(g):
    if g is None: return None
    t = g.get("type"); c = g.get("coordinates")
    if c is None: return None
    fmt = lambda p: f"{p[0]} {p[1]}"
    ring = lambda r: "(" + ", ".join(fmt(p) for p in r) + ")"
    try:
        if t == "Point":            return f"POINT ({fmt(c)})"
        if t == "MultiPoint":       return "MULTIPOINT (" + ", ".join(fmt(p) for p in c) + ")"
        if t == "LineString":       return "LINESTRING (" + ", ".join(fmt(p) for p in c) + ")"
        if t == "MultiLineString":  return "MULTILINESTRING (" + ", ".join(ring(L) for L in c) + ")"
        if t == "Polygon":          return "POLYGON (" + ", ".join(ring(r) for r in c) + ")"
        if t == "MultiPolygon":     return "MULTIPOLYGON (" + ", ".join("(" + ", ".join(ring(r) for r in poly) + ")" for poly in c) + ")"
    except Exception:
        return None
    return None


def write_layer(in_name, sample_n, label, asset_class, idx_writer):
    in_path = IN_DIR / in_name
    if not in_path.exists():
        print(f"  !! missing: {in_name}")
        return
    with gzip.open(in_path, "rt", encoding="utf-8") as f:
        fc = json.load(f)
    feats = fc.get("features", [])
    n_total = len(feats)
    if sample_n is not None and n_total > sample_n:
        feats = random.sample(feats, sample_n)
    n_kept = len(feats)
    if n_kept == 0:
        print(f"  [skip empty] {in_name}")
        return

    rows = []
    fields = set()
    for ft in feats:
        props = dict(ft.get("properties") or {})
        props["geometry_wkt"] = gj_to_wkt(ft.get("geometry"))
        props["geometry_type"] = (ft.get("geometry") or {}).get("type")
        rows.append(props)
        fields.update(props.keys())

    cols_priority = ["geometry_type", "geometry_wkt"]
    other_cols = sorted(c for c in fields if c not in cols_priority)
    cols = other_cols + cols_priority

    out_name = in_name.replace(".geojson.gz", ".csv")
    out_path = OUT_DIR / out_name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    sz = out_path.stat().st_size
    print(f"  {label:38} {n_kept:>6,}/{n_total:<7,} -> {out_name} ({sz/1024:.0f} KB)")
    idx_writer.writerow({
        "file": out_name,
        "asset_class": asset_class,
        "label": label,
        "geometry_type": rows[0].get("geometry_type"),
        "n_features": n_kept,
        "n_features_in_full": n_total,
        "n_attributes": len(other_cols),
    })


def main():
    print(f"Reading from: {IN_DIR}")
    print(f"Writing to:   {OUT_DIR}\n")
    idx_path = OUT_DIR / "_index.csv"
    with open(idx_path, "w", newline="", encoding="utf-8") as f:
        idx = csv.DictWriter(f, fieldnames=[
            "file", "asset_class", "label", "geometry_type",
            "n_features", "n_features_in_full", "n_attributes",
        ])
        idx.writeheader()
        for in_name, sample_n, label, asset_class in PICKS:
            write_layer(in_name, sample_n, label, asset_class, idx)
    print(f"\nIndex: {idx_path}")
    files = sorted(OUT_DIR.glob("*.csv"))
    total_sz = sum(p.stat().st_size for p in files)
    print(f"Done. {len(files)} CSV files, {total_sz/1024:.0f} KB total.")


if __name__ == "__main__":
    main()

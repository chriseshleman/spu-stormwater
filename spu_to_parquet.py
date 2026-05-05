#!/usr/bin/env python3
"""
Convert SPU GeoJSON files (gzipped) to Parquet.

One Parquet file per sub-layer, written to ~/Desktop/spu/parquet/.
Geometry is encoded as WKT text in a column named `geometry_wkt`,
which is compatible with DuckDB, BigQuery, PostgreSQL/PostGIS, and
geopandas (via shapely.from_wkt). Geometry type goes into a
separate `geometry_type` column.

Requires: pandas + pyarrow.  If not installed:
    pip3 install --user --trusted-host pypi.org --trusted-host files.pythonhosted.org pyarrow pandas

Resumable: skips Parquet files already present.
"""
import gzip
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

IN_DIR = Path.home() / "Desktop" / "spu" / "geojson"
OUT_DIR = Path.home() / "Desktop" / "spu" / "parquet"


# ---------------- GeoJSON geometry -> WKT (no shapely required) ---------------- #

def _coord(c):
    # ArcGIS may attach a third (z) value; we keep just (x, y) for portability
    return f"{c[0]} {c[1]}"

def _ring(r):
    return "(" + ", ".join(_coord(p) for p in r) + ")"

def gj_to_wkt(geom):
    if geom is None:
        return None
    t = geom.get("type")
    c = geom.get("coordinates")
    if c is None:
        return None
    try:
        if t == "Point":
            return f"POINT ({_coord(c)})"
        if t == "MultiPoint":
            return "MULTIPOINT (" + ", ".join(_coord(p) for p in c) + ")"
        if t == "LineString":
            return "LINESTRING (" + ", ".join(_coord(p) for p in c) + ")"
        if t == "MultiLineString":
            return "MULTILINESTRING (" + ", ".join(_ring(line) for line in c) + ")"
        if t == "Polygon":
            return "POLYGON (" + ", ".join(_ring(r) for r in c) + ")"
        if t == "MultiPolygon":
            return ("MULTIPOLYGON ("
                    + ", ".join("(" + ", ".join(_ring(r) for r in poly) + ")"
                                for poly in c) + ")")
    except Exception as e:
        return None
    return None


def convert_one(in_path: Path, out_path: Path):
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"  [skip] {out_path.name}")
        return out_path.stat().st_size, 0

    sys.stdout.write(f"  Loading {in_path.name} ... ")
    sys.stdout.flush()
    t0 = time.time()
    with gzip.open(in_path, "rt", encoding="utf-8") as f:
        fc = json.load(f)
    feats = fc.get("features", [])
    n = len(feats)
    sys.stdout.write(f"{n:,} features in {time.time()-t0:.1f}s\n")

    if n == 0:
        # write a near-empty parquet so downstream tooling sees a file
        df = pd.DataFrame(columns=["geometry_wkt", "geometry_type"])
        df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")
        return out_path.stat().st_size, 0

    # Build records: properties + geometry_wkt + geometry_type
    sys.stdout.write(f"  Converting geometry... ")
    sys.stdout.flush()
    t0 = time.time()
    records = []
    for ft in feats:
        props = ft.get("properties") or {}
        geom = ft.get("geometry")
        rec = dict(props)
        rec["geometry_wkt"] = gj_to_wkt(geom)
        rec["geometry_type"] = (geom or {}).get("type")
        records.append(rec)
    sys.stdout.write(f"done in {time.time()-t0:.1f}s\n")

    sys.stdout.write(f"  Writing parquet... ")
    sys.stdout.flush()
    t0 = time.time()
    df = pd.DataFrame.from_records(records)
    # All-null columns should keep dtype object — pandas does this naturally.
    df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")
    sys.stdout.write(f"done in {time.time()-t0:.1f}s\n")

    return out_path.stat().st_size, n


def main():
    if not IN_DIR.exists():
        sys.exit(f"Input dir not found: {IN_DIR}")

    OUT_DIR.mkdir(exist_ok=True)
    files = sorted(IN_DIR.glob("*.geojson.gz"))
    if not files:
        sys.exit(f"No .geojson.gz files in {IN_DIR}")

    print(f"Input dir:  {IN_DIR}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Files:      {len(files)}\n")

    total_features = 0
    total_bytes = 0
    started = time.time()
    summary = []
    for i, p in enumerate(files, 1):
        out_path = OUT_DIR / (p.stem.replace(".geojson", "") + ".parquet")
        print(f"[{i:>2}/{len(files)}] {p.name}")
        try:
            sz, n = convert_one(p, out_path)
            total_bytes += sz
            total_features += n
            summary.append({"file": out_path.name, "features": n, "bytes": sz})
        except Exception as e:
            print(f"  !! ERROR: {e}")
            summary.append({"file": p.name, "error": str(e)})
        print()

    with open(OUT_DIR / "manifest.json", "w") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_seconds": round(time.time() - started, 1),
            "total_features": total_features,
            "total_bytes": total_bytes,
            "files": summary,
        }, f, indent=2)

    print("=" * 60)
    print(f"DONE in {(time.time()-started)/60:.1f} minutes")
    print(f"  Files:    {len(files)}")
    print(f"  Features: {total_features:,}")
    print(f"  Total:    {total_bytes/1e6:.1f} MB Parquet")
    print(f"  Output:   {OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()

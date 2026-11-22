"""
Generate a self-contained HTML map of SPU stormwater assets within
the Pioneer Square / SODO / Elliott Bay bounding box, suitable for
hosting on GitHub Pages.

Output: ~/Desktop/spu/docs/index.html (single file, no external data
dependencies — all features embedded as GeoJSON in the HTML).
"""
import csv
import time
from pathlib import Path

import pandas as pd
import folium
from shapely import from_wkt
import geopandas as gpd

ROOT = Path.home() / "Desktop" / "spu"
SAMPLE_GEO = ROOT / "sample_geo"
# Output goes into a sibling folder that becomes the deployed-site repo.
OUT = Path.home() / "Desktop" / "spu-stormwater-map" / "index.html"

# Center of the bbox used by build_geo_sample.py
BBOX_CENTER = ((47.575 + 47.610) / 2, (-122.350 + -122.315) / 2)

# Layer styling (label -> color). Only layers present in sample_geo/_index.csv
# will actually be added; missing ones are skipped silently.
LAYER_SPECS = [
    # Polygons (drawn first / bottom)
    ("CSO Basins",                     "#7F77DD"),
    ("GSI Facility Footprints",        "#5DCAA5"),
    ("Other GSI Footprints",           "#9FE1CB"),
    ("Water Quality Polygons",         "#534AB7"),
    ("Vaults",                         "#1D9E75"),
    ("Misc Structures",                "#888780"),
    ("Pump Stations",                  "#3C3489"),
    # Lines (middle)
    ("Mainlines (Permitted Use)",      "#185FA5"),
    ("SPU-Owned Non-Mainlines",        "#85B7EB"),
    ("Force Mainlines",                "#0C447C"),
    ("Ditches & Culverts",             "#0F6E56"),
    ("GSI Swales",                     "#3B6D11"),
    ("GSI Underdrains & Rain Gardens", "#639922"),
    ("GSI Permeable Pavement",         "#97C459"),
    ("Curb & Gutter",                  "#5F5E5A"),
    # Points (drawn last / top)
    ("Storm Outfalls",                 "#993C1D"),
    ("Catch Basins",                   "#D85A30"),
    ("Sandboxes & Junction Boxes",     "#F0997B"),
    ("Mainline End Points",            "#444441"),
    ("Surface Drainage Points",        "#854F0B"),
    ("Water Quality Points",           "#E24B4A"),
    ("GSI Weirs",                      "#A32D2D"),
    ("Appurtenance Valves",            "#888780"),
]


def to_gdf(df, crs="EPSG:4326"):
    d = df.copy()
    d["geometry"] = d["geometry_wkt"].apply(from_wkt)
    return gpd.GeoDataFrame(d, geometry="geometry", crs=crs)


def add_layer(m, gdf, name, color, point_radius=3):
    geom_type = gdf.geometry.iloc[0].geom_type
    if geom_type == "Point":
        # Use a FeatureGroup so it shows up in LayerControl
        fg = folium.FeatureGroup(name=name)
        for _, row in gdf.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=point_radius, color=color, fill=True, fill_opacity=0.85,
                weight=0.5,
                popup=name,
            ).add_to(fg)
        fg.add_to(m)
    else:
        folium.GeoJson(
            gdf.to_json(),
            name=name,
            style_function=lambda _: {
                "color": color,
                "weight": 2,
                "fillColor": color,
                "fillOpacity": 0.18,
            },
            tooltip=name,
        ).add_to(m)


def build_legend_html(layer_counts):
    rows_html = []
    for label, color in LAYER_SPECS:
        if label not in layer_counts:
            continue
        rows_html.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
            f'<span style="width:12px;height:12px;background:{color};'
            f'border:0.5px solid #333;flex-shrink:0;"></span>'
            f'<span style="font-size:12px;">{label} '
            f'<span style="color:#888;">({layer_counts[label]:,})</span></span>'
            f'</div>'
        )
    return f"""
    <div style="
        position: fixed;
        bottom: 30px; left: 30px;
        z-index: 9999;
        background: white;
        padding: 12px 14px;
        border: 1px solid #888;
        border-radius: 6px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        max-width: 280px;
        max-height: 70vh;
        overflow-y: auto;
    ">
      <div style="font-weight: 600; margin-bottom: 8px;">Asset layers</div>
      {''.join(rows_html)}
    </div>
    """


def build_title_banner(total_features, layer_count):
    return f"""
    <div style="
        position: fixed;
        top: 12px; left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        background: white;
        padding: 10px 18px;
        border: 1px solid #888;
        border-radius: 6px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    ">
      <div style="font-size: 14px; font-weight: 600; margin: 0;">
        SPU Stormwater Asset Inventory — Pioneer Square / SODO / Elliott Bay
      </div>
      <div style="font-size: 11px; color: #555; margin-top: 2px;">
        {total_features:,} features across {layer_count} asset classes ·
        Source: <a href="https://data-seattlecitygis.opendata.arcgis.com/" target="_blank" style="color: #185FA5;">Seattle GeoData</a> ·
        Toggle layers in the controls (top-right)
      </div>
    </div>
    """


def main():
    OUT.parent.mkdir(exist_ok=True)
    started = time.time()

    print(f"Loading sample_geo/ from {SAMPLE_GEO}")
    index = pd.read_csv(SAMPLE_GEO / "_index.csv")
    print(f"  {len(index)} layers in index")

    geo_data = {
        row["label"]: pd.read_csv(SAMPLE_GEO / row["file"], low_memory=False)
        for _, row in index.iterrows()
    }

    m = folium.Map(
        location=BBOX_CENTER,
        zoom_start=14,
        tiles="OpenStreetMap",
        prefer_canvas=True,  # better performance with many features
    )

    layer_counts = {}
    for label, color in LAYER_SPECS:
        if label not in geo_data:
            print(f"  [skip — not in geo_data] {label}")
            continue
        df = geo_data[label]
        if len(df) == 0:
            print(f"  [skip — empty] {label}")
            continue
        gdf = to_gdf(df)
        add_layer(m, gdf, label, color)
        layer_counts[label] = len(gdf)
        print(f"  added {label}: {len(gdf):,} features ({color})")

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Custom HTML overlays — title at top, legend at bottom-left
    total_features = sum(layer_counts.values())
    m.get_root().html.add_child(folium.Element(
        build_title_banner(total_features, len(layer_counts))
    ))
    m.get_root().html.add_child(folium.Element(
        build_legend_html(layer_counts)
    ))

    print(f"\nWriting {OUT}")
    m.save(str(OUT))
    sz = OUT.stat().st_size
    print(f"  {sz:,} bytes ({sz/1e6:.1f} MB)")
    print(f"\nDone in {time.time() - started:.1f}s")
    print(f"\nOpen in browser:  open {OUT}")


if __name__ == "__main__":
    main()

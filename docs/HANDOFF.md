# Project Background and Decisions

The thinking behind the Seattle stormwater data work: what we set out to do, what we compared, what was built, and what is still open. For setup steps and file-level detail, see the [README](../README.md).

## Purpose

This project builds a real data foundation for an AI analytics tool aimed at owners of stormwater and flood control infrastructure. The work covered four things:

- Defining the asset types in a stormwater and flood control system.
- Finding an owner that publishes its asset data openly.
- Pulling and processing one owner's data: Seattle Public Utilities (SPU).
- Publishing a demo map of a downtown Seattle slice.

## Asset taxonomy

Seven categories describe what a stormwater and flood control system contains.

| Category | Examples |
|---|---|
| Conveyance | Pipes, culverts, open channels, ditches, tunnels |
| Collection and inlets | Catch basins, storm drains, curb inlets, grates |
| Detention and retention | Basins, ponds, underground vaults, cisterns |
| Pump stations | Facilities that move water where gravity is not enough |
| Outfalls and discharge | Structures that release water to the bay, ocean, or creeks |
| Green infrastructure | Bioswales, permeable pavement, rain gardens, living roofs |
| Flood barriers | Levees, floodwalls, tide gates, check valves |

Typical owners are municipal public works or utilities, or special flood control districts. Many owners cannot list their assets in one place. Boston Water and Sewer Commission, for example, publishes its inventory totals (nearly 600 miles of drain pipe, 30,327 catch basins, 207 outfalls, 9 pump stations) but not downloadable asset files.

## Which owner to use

We looked for an owner that publishes a complete, downloadable catalog.

| Owner | What it publishes | Gap |
|---|---|---|
| Seattle (SPU) | Mainlines, catch basins and inlets, outfalls, ditches and culverts, green infrastructure, vaults, ponds, drainage basins, pump stations and detention in a "Miscellaneous Structures" layer | No flood barriers |
| Philadelphia | Inlets, outfalls, green infrastructure, sewersheds | No pipe or pump-station layers found |
| Washington, DC | Outfalls, sewersheds | Pipe network is protected and not public |

No owner was fully complete. Seattle came closest, so it became the reference case.

## What was built

- A full pull of SPU's public layers: 17 FeatureServers, 59 sub-layers, 2,817,689 features in 54 files, snapshot April 28, 2026.
- Small sample files, a data dictionary, and an exploration notebook.
- An interactive map of Pioneer Square, SODO, and the Elliott Bay waterfront (about 18,000 features across 23 asset classes).

How each piece was made is in the [README](../README.md).

## Publishing

- Live map: https://chriseshleman.github.io/spu-stormwater-map/
- Map repo (output only): https://github.com/chriseshleman/spu-stormwater-map
- Analysis repo (code, samples, notebooks): https://github.com/chriseshleman/spu-stormwater
- The map's background tiles originally came from Carto, which now requires an API key. They were switched to OpenStreetMap tiles.

## Limits and open items

- The data is a point-in-time snapshot. Re-running the fetch gives current data, so counts will differ.
- The 2,817,689 total includes every lifecycle state. An earlier note cited about 2.75 million active features; that figure was not re-derived.
- SPU's public layers have no levees, floodwalls, or tide gates.
- The scripts assume the project folder sits at `~/Desktop/spu`.
- The code and documentation are released under the MIT license. SPU's data remains SPU's.

## Tools

Python (pandas, geopandas, shapely, folium), Jupyter in VS Code, git and GitHub, and SPU's public ArcGIS REST services. Claude was used for research and drafting.

# SPU Stormwater Sample — Data Dictionary

A plain-language guide to the columns you'll see across the 12 sample CSV files in `~/Desktop/spu/sample/`. Each row in any file is one physical asset (a pipe, a catch basin, an outfall, etc.). Field names mostly follow Seattle Public Utilities' internal naming, which uses short prefixes; the patterns below cover most of what's there.

## Universal columns — present in every file

| Column | What it is |
|---|---|
| `OBJECTID` | Internal database row ID. Use only as a unique key — not meaningful for analysis. |
| `geometry_wkt` | Where the asset is, written as text in standard "Well-Known Text" format (e.g., `POINT (-122.27 47.66)`). Universal across mapping tools. |
| `geometry_type` | `Point`, `LineString`, or `Polygon` — what kind of shape. |
| `lat`, `lon` | Latitude / longitude as plain numbers. For points, this is the asset's location. For lines and polygons, this is the geometry's centroid. Added by the loading notebook. |

## Common but not universal

| Column | What it is | Where you'll see it |
|---|---|---|
| `GlobalID` | Globally-unique cross-system ID — useful when joining against other SPU datasets. | ~6 of 12 layers |
| `Shape__Length` | Total length (feet) of the geometry — perimeter for polygons, full length for lines. | All polygon and line layers |
| `Shape__Area` | Area (square feet) of the geometry. | Polygon layers only |

## SPU's prefix convention

Every asset class uses a short prefix on its column names. The prefix tells you which type of asset the row represents:

| Prefix | Asset class |
|---|---|
| `OUT_` | Storm Outfalls |
| `MNL_` | Mainlines (pipes) |
| `PS_` | Pump Stations |
| `AP_` | Appurtenance Points (valves, GSI weirs) |
| `CB_` | Catch Basins |
| `DCH_` | Ditches & Culverts |
| `SDP_` | Surface Drainage / Underground Injection Points |
| `CSOB_` | CSO (Combined Sewer Overflow) Basins |
| `BSL_` | Bioswales (Green Stormwater Infrastructure) |
| `PLY_` | Polygon-based assets (Ponds, Vaults) |
| `SE_` | Standard equipment fields (Pump Stations, Vaults) |

## Field families — recurring patterns across layers

These are the conceptual building blocks you'll meet over and over, just with different prefixes. Wherever you see `*_FOO`, swap in the prefix above for the asset class you're looking at.

### Identifiers
| Pattern | Meaning |
|---|---|
| `*_FEA_KEY` | "Feature key." SPU's internal asset ID — the canonical reference for each asset. |
| `*_EQNUM_ID` | Equipment number from SPU's asset-management system. Often the human-readable label. |
| `*_<class>_ID` | Class-specific identifier (e.g., `OUT_OUTFALL_ID`, `PS_CSO_FCLTY_ID`). |

### Lifecycle and dates
| Pattern | Meaning |
|---|---|
| `*_LIFECYCLE_CODE` | One letter: typically `C` = current/active, `P` = proposed, `R`/`A` = retired/abandoned. |
| `*_LIFECYCLE_STAT` | The text version of the same. |
| `*_INSTALL_DATE` | When the asset entered service. |
| `*_RETIRE_DATE` | When the asset left service (null for active assets). |

### Ownership
| Pattern | Meaning |
|---|---|
| `*_OWNER_CODE` | Short code: typically `PUB` (Public/SPU), `PRI` (Private), or similar. |
| `*_OWNER_NAME` | Human-readable owner. Note: many side sewers are privately owned even though SPU tracks them. |

### Regulatory (federal Clean Water Act)
| Pattern | Meaning |
|---|---|
| `*_NPDES_ID` | Permit ID under the National Pollutant Discharge Elimination System (EPA-mandated). |
| `*_NPDES_ACTV_FLAG` | Whether the asset is currently subject to NPDES regulation. |
| `*_CSO_DESC` | Combined-sewer-overflow descriptor — relevant on outfalls and pump stations. |

### Network connectivity (pipes and mainline points)
| Pattern | Meaning |
|---|---|
| `*_UPS_ENDPT_ID`, `*_DNS_ENDPT_ID` | The upstream and downstream endpoints a pipe connects. |
| `*_CMPNT_KEY` | Component key linking the asset into the broader pipe-network topology. |
| `*_PIPE_FEA_KEY` | On non-pipe assets (outfalls, etc.): which pipe this asset belongs to. |

### Physical characteristics (pipes)
| Pattern | Meaning |
|---|---|
| `*_PIPE_MTRL_CODE` / `*_PIPE_MTRL_TEXT` | Pipe material — concrete, PVC, ductile iron, etc. |
| `*_PIPE_HGHT_IN_NBR` | Height (inches). For round pipes, equal to width = diameter. |
| `*_PIPE_WDTH_IN_NBR` | Width (inches). |
| `*_PRBL_FLOW_CODE` / `*_PRBL_FLOW_TEXT` | Probable direction of flow at this asset (e.g., separated stormwater vs combined sewer). |

### Drainage-area context
| Pattern | Meaning |
|---|---|
| `*_MAP_AREA_ID` | SPU's map-grid identifier — administrative region. |
| `*_DBASIN` | Drainage basin name (the geographic area whose runoff flows through this asset). |
| `*_SBASIN_ID` | Sub-basin ID — finer subdivision. |
| `*_REC_WTRBDY_NAME` | Receiving water body — where stormwater eventually discharges (e.g., Puget Sound, Lake Union, a creek). |
| `*_CWSHD_NAME` | Creek-watershed name. |

### Native coordinate columns
| Pattern | Meaning |
|---|---|
| `*_X_COORD`, `*_Y_COORD` | Washington State Plane coordinates (the projection SPU uses internally). |
| `*_LAT_COORD`, `*_LONG_COORD` | Lat/lon — only populated on some asset types (e.g., 100% on Appurtenances and GSI Weirs; only ~3% on Outfalls). For reliable lat/lon, use the `lat` / `lon` columns added by the loading notebook. |

## Layer-specific notables

### Storm Outfalls (`OUT_*`)
- `OUT_OUTFALL_ID`, `OUT_NPDES_ID`: regulatory IDs
- `OUT_REC_WTRBDY_NAME`: which body of water this outfall discharges to
- `OUT_CSO_DESC`: combined-sewer-overflow flag
- `OUT_OWNER_NAME`: 'Public', 'Private', or 'King County' — most outfalls are publicly owned

### Pump Stations (`PS_*`)
- `PS_PRI_RAIN_GAGE_ID`, `PS_SEC_RAIN_GAGE_ID`: which rain gauges feed this station's control logic
- `PS_DSCHRG1_FEATURE_KEY`, `PS_DSCHRG2_MNL_ENDPT_ID`: which mainlines this station discharges to
- `PS_CSO_FCLTY_ID`: links to a CSO control facility, if applicable

### Mainlines (`MNL_*`)
- `MNL_UPS_ENDPT_ID`, `MNL_DNS_ENDPT_ID`: how this pipe connects upstream and downstream
- `MNL_PIPE_MTRL_TEXT`, `MNL_PIPE_HGHT_IN_NBR`, `MNL_PIPE_WDTH_IN_NBR`: physical pipe specs
- `MNL_SSC2001_ID`: sewer-classification code (combined, separated storm, separated sanitary, etc.)
- `MNL_PRBL_FLOW_TEXT`: probable flow direction / regime

### Catch Basins (`CB_*`)
- `CB_TYPE_TEXT`: subtype (e.g., curb inlet, area drain)
- `CB_DEPTH_FT_NBR`: depth from surface
- `CB_PIPE_FEA_KEY`: which mainline it discharges to

### CSO Basins (`CSOB_*`)
- `CSOB_NAME`: human-readable basin name
- `CSOB_ACRES_NBR`: drainage area in acres

### Ditches & Culverts (`DCH_*`)
- `DCH_TYPE_TEXT`: open ditch vs. piped culvert
- `DCH_PIPE_MTRL_TEXT`: material (for culverts)

### Surface Drainage / Underground Injection (`SDP_*`)
- `SDP_TYPE_TEXT`: subtype
- `SDP_PIPE_FEA_KEY`: receiving pipe

### Ponds & Vaults (`PLY_*` + `SE_*`)
- `PLY_VOL_CF_NBR`: storage volume (cubic feet)
- `SE_DESC_TEXT`: free-text description

### Green Stormwater Infrastructure (`AP_*`, `BSL_*`)
- `AP_TYPE_TEXT`: asset subtype (weir, swale, rain garden, permeable pavement, etc.)
- `BSL_LENGTH_FT_NBR`: bioswale length

### Appurtenance Valves (`AP_*`)
- `AP_TYPE_TEXT`: valve type (e.g., gate valve, check valve)
- `AP_PIPE_FEA_KEY`: which pipe this valve sits on

## Quick gotchas

- **Sparse fields are common.** A field's existence in the schema doesn't mean it's filled in. NPDES IDs, install dates, and material attributes are often null on many records.
- **Lifecycle codes vary by layer.** `C` is the most common "active" indicator but some layers use other letters; always check `*_LIFECYCLE_STAT` for the readable version.
- **"Mainlines (Probable Flow)" and "Mainlines (Permitted Use)" share the same physical pipes**, just rendered with different attribute focus. Don't double-count.
- **Many "non-mainlines" are private side sewers**, not assets SPU operates and maintains. Filter on `*_OWNER_*` if you want only publicly-owned infrastructure.
- **Coordinate units differ.** Native `*_X_COORD` / `*_Y_COORD` are in Washington State Plane feet; the `lat` / `lon` columns added by the loading notebook are decimal degrees (WGS84). Don't mix them.

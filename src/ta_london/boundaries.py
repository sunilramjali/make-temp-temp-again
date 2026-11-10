"""London borough boundaries for maps.

Source: ONS Local Authority Districts (May 2024) Boundaries UK BGC (generalised, 20m, clipped),
London features only (LAD24CD starting E09), downloaded as GeoJSON in WGS84. The raw file stays
untouched in data/raw/ons/; this module writes a checked copy keyed on `area_code` to
data/reference/ for the app to draw.
"""

import geopandas as gpd

from ta_london.geography import load_boroughs
from ta_london.paths import RAW, REFERENCE

RAW_BOUNDARIES = RAW / "ons" / "LAD_MAY_2024_UK_BGC_london.geojson"
BOUNDARIES_GEOJSON = REFERENCE / "london_boroughs.geojson"
CODE_FIELD = "LAD24CD"


def build_london_boundaries(gdf: gpd.GeoDataFrame, expected_codes: set[str]) -> gpd.GeoDataFrame:
    """Keep London boroughs, key them on `area_code`, reproject to WGS84 and check that
    every expected borough is present exactly once."""
    if CODE_FIELD not in gdf.columns:
        raise ValueError(f"Boundary file has no {CODE_FIELD} column: {list(gdf.columns)}")
    if gdf.crs is None:
        raise ValueError("Boundary file has no CRS")
    out = gdf[gdf[CODE_FIELD].astype(str).str.startswith("E09")]
    out = out.rename(columns={CODE_FIELD: "area_code"})[["area_code", "geometry"]]
    out = out.to_crs(4326).sort_values("area_code").reset_index(drop=True)
    codes = list(out["area_code"])
    if len(codes) != len(set(codes)) or set(codes) != expected_codes:
        missing = sorted(expected_codes - set(codes))
        extra = sorted(set(codes) - expected_codes)
        raise ValueError(
            f"Boundary codes don't match the borough lookup: missing {missing}, extra {extra}, "
            f"{len(codes)} features"
        )
    return out


def write_london_boundaries(raw=RAW_BOUNDARIES, path=BOUNDARIES_GEOJSON) -> bool:
    """Rebuild the reference GeoJSON if the raw file exists. Returns whether it was written."""
    if not raw.exists():
        return False
    expected = set(load_boroughs()["area_code"])
    out = build_london_boundaries(gpd.read_file(raw), expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(path, driver="GeoJSON")
    return True

import geopandas as gpd
import pytest
from shapely.geometry import box

from ta_london.boundaries import build_london_boundaries

CODES = {"E09000001", "E09000025"}


def frame(codes, crs="EPSG:27700"):
    # British National Grid boxes in central/east London.
    geoms = [box(530000 + i * 1000, 180000, 531000 + i * 1000, 181000) for i in range(len(codes))]
    return gpd.GeoDataFrame({"LAD24CD": codes, "LAD24NM": codes}, geometry=geoms, crs=crs)


def test_keeps_london_reprojects_and_renames():
    out = build_london_boundaries(frame(["E09000025", "E06000047", "E09000001"]), CODES)
    assert list(out["area_code"]) == ["E09000001", "E09000025"]
    assert list(out.columns) == ["area_code", "geometry"]
    assert out.crs.to_epsg() == 4326
    minx, miny, maxx, maxy = out.total_bounds
    assert -0.3 < minx < maxx < 0.1 and 51.4 < miny < maxy < 51.6


def test_missing_borough_fails():
    with pytest.raises(ValueError, match="missing"):
        build_london_boundaries(frame(["E09000025"]), CODES)


def test_duplicate_borough_fails():
    with pytest.raises(ValueError, match="don't match"):
        build_london_boundaries(frame(["E09000025", "E09000025", "E09000001"]), CODES)


def test_missing_code_column_fails():
    with pytest.raises(ValueError, match="LAD24CD"):
        build_london_boundaries(frame(["E09000025"]).rename(columns={"LAD24CD": "x"}), CODES)

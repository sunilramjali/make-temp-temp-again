"""Every page must load without exceptions, with or without pipeline output."""

import pytest
from streamlit.testing.v1 import AppTest

from ta_london.paths import PROCESSED, ROOT

PAGES = ["Home.py"] + [f"pages/{p.name}" for p in sorted((ROOT / "app" / "pages").glob("*.py"))]
HAS_DATA = (PROCESSED / "indicators.parquet").exists()
CHART_PAGES = [
    "pages/1_London_boroughs.py",
    "pages/2_Demographics.py",
    "pages/3_Current_solution.py",
    "pages/4_Social_housing.py",
]


def run(page):
    return AppTest.from_file(str(ROOT / "app" / page), default_timeout=60).run()


@pytest.mark.parametrize("page", PAGES)
def test_page_loads(page, monkeypatch):
    # Never start a real 2-minute build from a smoke test.
    monkeypatch.setenv("TA_LONDON_NO_AUTOBUILD", "1")
    assert not run(page).exception


@pytest.mark.skipif(not HAS_DATA, reason="run the pipeline first")
@pytest.mark.parametrize("page", CHART_PAGES)
def test_data_pages_draw_charts_when_data_exists(page):
    at = run(page)
    assert not at.exception
    assert len(at.get("plotly_chart")) >= 1, "page drew no charts"
    assert not [w for w in at.warning if "No data loaded" in w.value]


@pytest.mark.skipif(
    not (HAS_DATA and (ROOT / "data" / "reference" / "london_boroughs.geojson").exists()),
    reason="run the pipeline with the ONS boundary file first",
)
def test_social_housing_draws_borough_maps():
    at = run("pages/4_Social_housing.py")
    assert not at.exception
    maps = [c for c in at.get("plotly_chart") if '"choropleth"' in c.proto.spec]
    assert len(maps) == 2


@pytest.mark.skipif(
    not (HAS_DATA and (ROOT / "data" / "reference" / "london_boroughs.geojson").exists()),
    reason="run the pipeline with the ONS boundary file first",
)
def test_london_boroughs_draws_map_for_default_rate_indicator():
    at = run("pages/1_London_boroughs.py")
    assert not at.exception
    maps = [c for c in at.get("plotly_chart") if '"choropleth"' in c.proto.spec]
    assert len(maps) == 1

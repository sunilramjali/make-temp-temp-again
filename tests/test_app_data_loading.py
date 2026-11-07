"""Regression tests for the 'No data loaded' problem (see docs/postmortems/).

1. A fresh clone has no processed table: the app must build it, not show empty pages.
2. If the table appears after a page was opened, it must show without restarting the server
   (load_data used to cache 'no data' forever).
"""

import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from ta_london.paths import ROOT
from ta_london.schema import COLUMNS

sys.path.insert(0, str(ROOT / "app"))
import components  # noqa: E402

HOME = str(ROOT / "app" / "Home.py")


def tiny_table(path):
    df = pd.DataFrame(
        [
            {
                "area_code": "E09000025",
                "area_name": "Newham",
                "period": "2026-Q1",
                "period_type": "quarter_end",
                "period_end": pd.Timestamp("2026-03-31"),
                "indicator": "ta_households",
                "breakdown": "all",
                "value": 7561.0,
                "value_status": "ok",
                "unit": "households",
                "source_id": "mhclg_la_detailed_2026q1",
            }
        ],
        columns=COLUMNS,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


@pytest.fixture
def missing_table(tmp_path, monkeypatch):
    path = tmp_path / "processed" / "indicators.parquet"
    monkeypatch.setattr(components, "INDICATORS_PARQUET", path)
    return path


def warnings(at):
    return [w.value for w in at.warning]


def test_no_data_and_autobuild_off_shows_clear_message(missing_table, monkeypatch):
    monkeypatch.setenv(components.NO_AUTOBUILD_ENV, "1")
    at = AppTest.from_file(HOME, default_timeout=30).run()
    assert not at.exception
    assert any("No data loaded" in w for w in warnings(at))


def test_no_data_triggers_a_build(missing_table, monkeypatch):
    monkeypatch.delenv(components.NO_AUTOBUILD_ENV, raising=False)
    calls = []

    def fake_run():
        calls.append(1)
        tiny_table(missing_table)

    monkeypatch.setattr(components.pipeline, "run", fake_run)
    at = AppTest.from_file(HOME, default_timeout=30).run()
    assert not at.exception
    assert calls == [1]
    assert not any("No data loaded" in w for w in warnings(at))


def test_failed_build_shows_the_reason(missing_table, monkeypatch):
    monkeypatch.delenv(components.NO_AUTOBUILD_ENV, raising=False)

    def broken():
        raise FileNotFoundError("Raw file missing: data/raw/x.ods")

    monkeypatch.setattr(components.pipeline, "run", broken)
    at = AppTest.from_file(HOME, default_timeout=30).run()
    assert not at.exception
    assert any("Raw file missing" in w for w in warnings(at))


def test_table_created_later_shows_without_restart(missing_table, monkeypatch):
    monkeypatch.setenv(components.NO_AUTOBUILD_ENV, "1")
    at = AppTest.from_file(HOME, default_timeout=30).run()
    assert any("No data loaded" in w for w in warnings(at))
    tiny_table(missing_table)  # e.g. someone runs the pipeline in a terminal
    at.run()
    assert not any("No data loaded" in w for w in warnings(at))

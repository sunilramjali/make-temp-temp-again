import math

import pytest

from fixtures import NAMES, lt600_frames
from ta_london.ingest import waiting_list
from ta_london.schema import validate


def parse():
    la, imp = lt600_frames()
    return waiting_list.parse_lt600(la, imp, "test_source", NAMES)


def row(df, code, year_end):
    r = df[(df.area_code == code) & (df.period == year_end)]
    assert len(r) == 1
    return r.iloc[0]


def test_only_london_boroughs_and_years_from_2012():
    df = parse()
    assert set(df["area_code"]) == {"E09000025"} | set()  # Croydon not in the test lookup
    assert "2011-04-01" not in set(df["period"])


def test_reference_date_is_1_april_up_to_2018_then_31_march():
    df = parse()
    assert row(df, "E09000025", "2018-04-01")["value"] == 26139
    assert row(df, "E09000025", "2019-03-31")["value"] == 27635
    assert set(df["period_type"]) == {"snapshot"}


def test_imputed_value_flagged_estimated(monkeypatch):
    names = {**NAMES, "E09000008": "Croydon"}
    la, imp = lt600_frames()
    df = waiting_list.parse_lt600(la, imp, "test_source", names)
    assert row(df, "E09000008", "2022-03-31")["value_status"] == "estimated"
    assert row(df, "E09000008", "2022-03-31")["value"] == 5470
    assert row(df, "E09000008", "2019-03-31")["value_status"] == "ok"


def test_missing_marker_is_nan():
    names = {**NAMES, "E09000008": "Croydon"}
    la, imp = lt600_frames()
    df = waiting_list.parse_lt600(la, imp, "test_source", names)
    r = row(df, "E09000008", "2018-04-01")
    assert math.isnan(r["value"]) and r["value_status"] == "missing"


def test_passes_schema():
    validate(parse())


def test_bad_cell_fails_loudly():
    la, imp = lt600_frames()
    la.iloc[4, 9] = "lots"
    with pytest.raises(ValueError, match="Unrecognised"):
        waiting_list.parse_lt600(la, imp, "test_source", NAMES)

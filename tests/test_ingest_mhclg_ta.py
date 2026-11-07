import math

import pytest

from fixtures import NAMES, ta_sheets
from ta_london.ingest import mhclg_ta
from ta_london.schema import validate

SOURCE = "test_source"


def parse(**kw):
    return mhclg_ta.parse_ta_sheets(ta_sheets(**kw), SOURCE, NAMES)


def pick(df, area, indicator, breakdown="all"):
    row = df[(df.area_code == area) & (df.indicator == indicator) & (df.breakdown == breakdown)]
    assert len(row) == 1, (area, indicator, breakdown, len(row))
    return row.iloc[0]


def test_period_read_from_title():
    df = parse()
    assert set(df["period"]) == {"2026-Q1"}
    assert set(df["period_end"].dt.strftime("%Y-%m-%d")) == {"2026-03-31"}
    assert set(df["period_type"]) == {"quarter_end"}


def test_only_london_and_england_rows_kept():
    df = parse()
    assert set(df["area_code"]) == set(NAMES)


def test_london_duplicate_row_dropped():
    df = parse()
    assert len(df[(df.area_code == "E12000007") & (df.indicator == "ta_households")]) == 1


def test_code_with_leading_newline_is_cleaned():
    assert pick(parse(), "E09000001", "ta_households")["area_name"] == "City of London"


def test_value_and_names():
    row = pick(parse(newham_value=7561.0), "E09000025", "ta_households")
    assert row["value"] == 7561.0 and row["value_status"] == "ok"
    assert row["area_name"] == "Newham"
    assert row["unit"] == "households"


def test_suppressed_marker_is_nan_with_status():
    row = pick(parse(), "E09000001", "ta_households")
    assert math.isnan(row["value"]) and row["value_status"] == "suppressed"


def test_zero_length_of_stay_is_missing_not_zero():
    row = pick(parse(newham_value=0.0), "E09000025", "ta_length_of_stay_median_days", "bnb")
    assert math.isnan(row["value"]) and row["value_status"] == "missing"
    # a zero count elsewhere stays a real zero
    assert pick(parse(newham_value=0.0), "E09000025", "ta_households")["value"] == 0.0


def test_output_passes_tidy_schema():
    validate(parse())


def test_renamed_column_fails_loudly():
    sheets = ta_sheets()
    sheets["TA5"].iloc[5, 3] = "Sixteen to seventeen"
    with pytest.raises(ValueError, match="TA5"):
        mhclg_ta.parse_ta_sheets(sheets, SOURCE, NAMES)


def test_unreadable_snapshot_date_fails():
    sheets = ta_sheets()
    sheets["TA1"].iloc[0, 0] = "Table TA1 - no date here"
    with pytest.raises(ValueError, match="snapshot date"):
        mhclg_ta.parse_ta_sheets(sheets, SOURCE, NAMES)


def test_unknown_cell_text_fails_loudly():
    sheets = ta_sheets()
    sheets["TA2"].iloc[11, 2] = "n/a"
    with pytest.raises(ValueError, match="Unrecognised"):
        mhclg_ta.parse_ta_sheets(sheets, SOURCE, NAMES)

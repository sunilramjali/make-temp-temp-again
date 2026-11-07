import pandas as pd
import pytest

from ta_london.ingest import gla_council_homes as gla
from ta_london.schema import validate

YEARS = ["2018-19 (From Sept 18)", "2019-20", "2025-26", "2026-27"]


def names33():
    return {f"E09{n:06d}": f"Borough {n}" for n in range(1, 34)}


def table(extra_name=None):
    width = 2 + 2 * (len(YEARS) + 1)
    rows = [
        ["", "Table 2: Council Homes delivered via GLA programmes"] + [""] * (width - 2),
        ["", "To end of June 2026"] + [""] * (width - 2),
        # Same layout as the real sheet: the group label sits above each 'Local Authority' column.
        ["", "Starts on site"] + [""] * len(YEARS) + ["Completions"] + [""] * len(YEARS),
        ["", "Total", "1", "2", "3", "4", "Total", "1", "2", "3", "4", ""],
        ["", "Local Authority", *YEARS, "Local Authority", *YEARS, ""],
    ]
    for n in range(1, 34):
        name = f"Borough {n}"
        rows.append(["", name, "10", "20", "30", "99", name, "1", "2", "3", "99", ""])
    rows.append(
        [
            "",
            "Multiple London Boroughs",
            "0",
            "0",
            "50",
            "0",
            "Multiple London Boroughs",
            "0",
            "0",
            "0",
            "82",
            "",
        ]
    )
    if extra_name:
        rows.append(["", extra_name, "1", "1", "1", "1", extra_name, "1", "1", "1", "1", ""])
    return pd.DataFrame(rows)


def test_starts_and_completions_by_financial_year():
    df = gla.parse_table_2(table(), "s", names33())
    assert set(df.indicator) == {"council_homes_started_gla", "council_homes_completed_gla"}
    assert set(df.period) == {"2018-19", "2019-20", "2025-26"}  # partial 2026-27 left out
    r = df[
        (df.area_code == "E09000001")
        & (df.indicator == "council_homes_completed_gla")
        & (df.period == "2025-26")
    ].iloc[0]
    assert r.value == 3 and str(r.period_end.date()) == "2026-03-31"
    validate(df)


def test_multiple_boroughs_row_is_left_out():
    df = gla.parse_table_2(table(), "s", names33())
    assert df.area_code.nunique() == 33


def test_unknown_borough_name_fails_loudly():
    with pytest.raises(ValueError, match="not in the ONS lookup"):
        gla.parse_table_2(table(extra_name="Borough of Nowhere"), "s", names33())

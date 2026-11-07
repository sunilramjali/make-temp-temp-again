import math

import pandas as pd
import pytest

from fixtures import NAMES
from ta_london.ingest import lettings
from ta_london.schema import validate

LEAVES = lettings._LEAF_LABELS


def frame_1d():
    header = [
        "Financial year",
        "Region Code",
        "Region Name",
        "LA Code at time of letting [note 8]",
        "LA Name at time of letting [note 9]",
        "Total",
        *[f"{label} [note 10]" if label.endswith("LA") else label for label in LEAVES],
    ]
    n = len(LEAVES)
    return pd.DataFrame(
        [
            ["Table 1d: New social housing lettings, 2009/10 to 2024/25"] + [None] * (n + 5),
            ["This worksheet contains one table."] + [None] * (n + 5),
            ["This table contains notes."] + [None] * (n + 5),
            ["Source: CORE"] + [None] * (n + 5),
            header,
            ["2024/25", "E12000007", "London", "E09000025", "Newham", 711] + [1] * n,
            ["2023/24", "E12000007", "London", "E09000025", "Newham", 966] + [2] * n,
            ["2009/10", "E12000007", "London", "00BB", "Newham", 919] + [3] * n,
            ["2024/25", "E12000001", "North East", "E06000047", "Durham", 4005] + [4] * n,
        ]
    )


def frame_1e(market="390.23"):
    header = [
        "Region Code",
        "Region Name",
        "LA Code at time of letting",
        "LA Name at time of letting [note 9] [note 16]",
        "Average weekly rent for social housing re-lets (£) [note 15]",
        "Average weekly market rent (£) [note 15]",
        "Average weekly rent for a re-let as a proportion of market rent (%) [note 15]",
        "New social housing re-lets",
        "Total social stock at 1 April",
        "Proportion of social stock re-let (%)",
    ]
    return pd.DataFrame(
        [
            ["Table 1e: Social housing churn by local authority, 2024/25 (re-lets only)"]
            + [None] * 9,
            ["This worksheet contains one table."] + [None] * 9,
            ["This table contains notes."] + [None] * 9,
            ["Source: ONS"] + [None] * 9,
            header,
            ["E12000007", "London", "E09000025", "Newham", 160.26, 390.23, 41.1, 448, 31666, 1.4],
            [
                "E12000007",
                "London",
                "E09000001",
                "City of London",
                136.92,
                market,
                None,
                17,
                681,
                2.5,
            ],
        ]
    )


def test_1d_keeps_london_codes_and_financial_years():
    df = lettings.parse_table_1d(frame_1d(), "src", NAMES)
    assert set(df["area_code"]) == {"E09000025"}
    assert set(df["period"]) == {"2024-25", "2023-24"}  # old '00BB' code and Durham dropped
    r = df[(df.period == "2024-25") & (df.indicator == "social_lettings_total")].iloc[0]
    assert r["value"] == 711 and str(r["period_end"].date()) == "2025-03-31"
    assert set(df["period_type"]) == {"financial_year"}


def test_1d_has_one_row_per_leaf():
    df = lettings.parse_table_1d(frame_1d(), "src", NAMES)
    leaves = df[(df.period == "2024-25") & (df.indicator == "social_lettings_by_type")]
    assert len(leaves) == 12 and "sr_general_needs_la" in set(leaves["breakdown"])


def test_1d_missing_column_fails():
    f = frame_1d()
    f.iloc[4, 6] = "Something else"
    with pytest.raises(ValueError, match="Table_1d"):
        lettings.parse_table_1d(f, "src", NAMES)


def test_1e_period_from_title_and_values():
    df = lettings.parse_table_1e(frame_1e(), "src", NAMES)
    assert set(df["period"]) == {"2024-25"}
    r = df[(df.area_code == "E09000025") & (df.indicator == "social_relet_rate")].iloc[0]
    assert r["value"] == 1.4 and r["unit"] == "percent"


def test_1e_blank_value_is_missing():
    df = lettings.parse_table_1e(frame_1e(), "src", NAMES)
    r = df[(df.area_code == "E09000001") & (df.indicator == "social_rent_pct_of_market_rent")].iloc[
        0
    ]
    assert math.isnan(r["value"]) and r["value_status"] == "missing"


def test_outputs_pass_schema():
    validate(lettings.parse_table_1d(frame_1d(), "src", NAMES))
    validate(lettings.parse_table_1e(frame_1e(), "src", NAMES))

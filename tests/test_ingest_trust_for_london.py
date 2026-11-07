import pandas as pd
import pytest

from fixtures import NAMES
from ta_london.ingest import trust_for_london as tfl
from ta_london.schema import validate

T87_HEADER = [
    "Year",
    "Total number of households in TA",
    "Containing children",
    "B&B",
    "Nightly paid, self contained accommodation",
    "Hostels (incl. refuges)",
    "Private rented sector via local authority/housing association",
    "Local authority or Housing association stock",
    "Any other type of temporary accommodation",
    "In TA in another local authority district",
    "Duty owed, no accommodation secured",
]
T88_HEADER = [
    "Area",
    "ONS code",
    "All households (000s)",
    "Total households in temporary accommodation",
    "Households in temporary accommodation per 1,000 households",
    "Households in temporary accommodation in another local authority district",
    "Households in temporary accommodation with children",
    "Households in temporary accommodation in another local authority district per 1,000 "
    "households",
    "Households in temporary accommodation with children per 1,000 households",
]


def t87():
    blank = [""] * 11
    return pd.DataFrame(
        [
            ["Temporary accommodation types in London (2002-2025)"] + [""] * 10,
            blank,
            T87_HEADER,
            [
                "2002",
                "48678",
                "35465",
                "9048",
                "3655",
                "4175",
                "19075",
                "10482",
                "2238",
                "9132",
                "4102",
            ],
            [
                "2025",
                "74860",
                "49648",
                "4612",
                "34168",
                "2850",
                "18155",
                "13455",
                "1618",
                "34318",
                "610",
            ],
            blank,
            ["Note: New categories do not count towards TA total."] + [""] * 10,
        ]
    )


def t88(boroughs=33):
    rows = [
        ["Proportion of households in temporary accommodation in London boroughs (2025 Q4)"]
        + [""] * 8,
        [""] * 9,
        T88_HEADER,
        ["England", "E92000001", "24440", "133130", "5.45", "41980", "84730", "1.72", "3.47"],
        ["London", "E12000007", "3659", "74860", "20.46", "34320", "49650", "9.38", "13.57"],
    ]
    for n in range(1, boroughs + 1):
        rows.append([f"B{n}", f"E09{n:06d}", "100", "1000", "10", "100", "500", "1", "5"])
    rows.append(["Note: average of 4 quarters"] + [""] * 8)
    return pd.DataFrame(rows)


def names33():
    return {**{f"E09{n:06d}": f"B{n}" for n in range(1, 34)}, **NAMES}


def test_t87_is_london_calendar_year_averages():
    df = tfl.parse_t87(t87(), "s", NAMES)
    assert set(df.area_code) == {"E12000007"}
    assert set(df.period) == {"2002", "2025"}
    assert set(df.period_type) == {"calendar_year_average"}
    r = df[(df.indicator == "ta_households_avg4q") & (df.period == "2025")].iloc[0]
    assert r.value == 74860 and str(r.period_end.date()) == "2025-12-31"
    validate(df)


def test_t87_types_are_breakdowns_of_one_indicator():
    df = tfl.parse_t87(t87(), "s", NAMES)
    types = df[df.indicator == "ta_households_by_accommodation_type_avg4q"]
    assert set(types.breakdown) == {
        "bnb",
        "nightly_paid",
        "hostel",
        "private_sector",
        "la_ha_stock",
        "other",
    }


def test_t87_renamed_column_fails():
    f = t87()
    f.iloc[2, 3] = "Bed and breakfast"
    with pytest.raises(ValueError, match="T87"):
        tfl.parse_t87(f, "s", NAMES)


def test_t88_period_and_rates():
    df = tfl.parse_t88(t88(), "s", names33())
    assert set(df.period) == {"2025"}
    r = df[(df.area_code == "E12000007") & (df.indicator == "ta_households_per_1000_avg4q")]
    assert r.iloc[0].value == 20.46
    validate(df)


def test_t88_missing_boroughs_fails():
    with pytest.raises(ValueError, match="33 London boroughs"):
        tfl.parse_t88(t88(boroughs=32), "s", names33())

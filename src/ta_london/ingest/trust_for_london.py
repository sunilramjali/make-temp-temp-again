"""Trust for London, London's Poverty Profile 2026: charts T87 and T88 (CSV downloads).

Both are compiled by Trust for London from MHCLG tables and are averages of four quarters, not
end-of-quarter counts, so they get their own indicators (suffix _avg4q) and the period type
calendar_year_average. They are not mixed with the MHCLG snapshot indicators.

T87: London only, 2002-2025, households in TA by type. The 2002-2018 and 2019-2025 figures come
     from different MHCLG collections (P1E, then H-CLIC), so there is a series break.
T88: London boroughs, London and England, average of the four quarters to 2025 Q4. Counts appear
     rounded to the nearest 10.
"""

import re
from datetime import date

import pandas as pd

from ta_london.geography import LONDON_CODE, area_name_lookup
from ta_london.ingest.common import clean_code, clean_label, column_index, parse_value, tidy

PERIOD_TYPE = "calendar_year_average"

_T87_COLUMNS = [
    ("Total number of households in TA", "ta_households_avg4q", "all"),
    ("Containing children", "ta_households_with_children_avg4q", "all"),
    ("B&B", "ta_households_by_accommodation_type_avg4q", "bnb"),
    (
        "Nightly paid, self contained accommodation",
        "ta_households_by_accommodation_type_avg4q",
        "nightly_paid",
    ),
    ("Hostels (incl. refuges)", "ta_households_by_accommodation_type_avg4q", "hostel"),
    (
        "Private rented sector via local authority/housing association",
        "ta_households_by_accommodation_type_avg4q",
        "private_sector",
    ),
    (
        "Local authority or Housing association stock",
        "ta_households_by_accommodation_type_avg4q",
        "la_ha_stock",
    ),
    (
        "Any other type of temporary accommodation",
        "ta_households_by_accommodation_type_avg4q",
        "other",
    ),
    ("In TA in another local authority district", "ta_households_out_of_area_avg4q", "all"),
    (
        "Duty owed, no accommodation secured",
        "ta_households_duty_owed_no_accommodation_avg4q",
        "all",
    ),
]

_T88_COLUMNS = [
    ("All households (000s)", "households_in_area_avg4q", "thousand_households"),
    ("Total households in temporary accommodation", "ta_households_avg4q", "households"),
    (
        "Households in temporary accommodation per 1,000 households",
        "ta_households_per_1000_avg4q",
        "per_1000_households",
    ),
    (
        "Households in temporary accommodation in another local authority district",
        "ta_households_out_of_area_avg4q",
        "households",
    ),
    (
        "Households in temporary accommodation with children",
        "ta_households_with_children_avg4q",
        "households",
    ),
    (
        "Households in temporary accommodation in another local authority district per 1,000 "
        "households",
        "ta_households_out_of_area_per_1000_avg4q",
        "per_1000_households",
    ),
    (
        "Households in temporary accommodation with children per 1,000 households",
        "ta_households_with_children_per_1000_avg4q",
        "per_1000_households",
    ),
]


def _read_csv(path) -> pd.DataFrame:
    return pd.read_csv(path, header=None, dtype=str, keep_default_na=False)


def _header_row(df: pd.DataFrame, first_cell: str) -> int:
    for i in range(min(10, len(df))):
        if df.iloc[i, 0].strip() == first_cell:
            return i
    raise ValueError(f"No header row starting {first_cell!r}")


def _record(code, names, period, end, indicator, breakdown, raw, unit, source_id):
    value, status = parse_value(raw if raw != "" else None)
    return {
        "area_code": code,
        "area_name": names[code],
        "period": period,
        "period_type": PERIOD_TYPE,
        "period_end": end,
        "indicator": indicator,
        "breakdown": breakdown,
        "value": value,
        "value_status": status,
        "unit": unit,
        "source_id": source_id,
    }


def parse_t87(
    df: pd.DataFrame, source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    names = names or area_name_lookup()
    if "London" not in df.iloc[0, 0]:
        raise ValueError(f"T87: unexpected title {df.iloc[0, 0]!r}")
    h = _header_row(df, "Year")
    labels = [clean_label(v) for v in df.iloc[h]]
    cols = [(column_index(labels, lbl, "T87"), ind, bd) for lbl, ind, bd in _T87_COLUMNS]
    records = []
    for _, row in df.iloc[h + 1 :].iterrows():
        year = row.iloc[0].strip()
        if not re.fullmatch(r"\d{4}", year):
            continue  # blank lines and footnotes
        for col, indicator, breakdown in cols:
            records.append(
                _record(
                    LONDON_CODE,
                    names,
                    year,
                    date(int(year), 12, 31),
                    indicator,
                    breakdown,
                    row.iloc[col],
                    "households",
                    source_id,
                )
            )
    return tidy(records)


def t88_period(df: pd.DataFrame) -> tuple[str, date]:
    title = df.iloc[0, 0]
    m = re.search(r"\((\d{4}) Q4\)", title)
    if not m:
        raise ValueError(f"T88: cannot read the period from the title {title!r}")
    year = int(m.group(1))
    return str(year), date(year, 12, 31)


def parse_t88(
    df: pd.DataFrame, source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    names = names or area_name_lookup()
    period, end = t88_period(df)
    h = _header_row(df, "Area")
    labels = [clean_label(v) for v in df.iloc[h]]
    code_col = column_index(labels, "ONS code", "T88")
    cols = [(column_index(labels, lbl, "T88"), ind, unit) for lbl, ind, unit in _T88_COLUMNS]
    records = []
    for _, row in df.iloc[h + 1 :].iterrows():
        code = clean_code(row.iloc[code_col])
        if code not in names:
            continue
        for col, indicator, unit in cols:
            records.append(
                _record(code, names, period, end, indicator, "all", row.iloc[col], unit, source_id)
            )
    out = tidy(records)
    boroughs = out[out["area_code"].str.startswith("E09")]["area_code"].nunique()
    if boroughs != 33:
        raise ValueError(f"T88: expected 33 London boroughs, found {boroughs}")
    return out


def load_t87(path, source_id, names=None) -> pd.DataFrame:
    return parse_t87(_read_csv(path), source_id, names)


def load_t88(path, source_id, names=None) -> pd.DataFrame:
    return parse_t88(_read_csv(path), source_id, names)

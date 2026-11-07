"""MHCLG statutory homelessness: detailed local authority tables, TA1 to TA8.

Layout (checked against the Jan to Mar 2026 release): one header row starting
"Organisation Identification Code"; one row per area with the ONS code in column 0; markers
[c] suppressed, [x] missing, [z] not applicable. Columns are found by header text, never by
position, and a missing or renamed column raises an error.

Only the 33 London boroughs plus London and England rows are kept.
"""

import math
import re
from datetime import date

import pandas as pd

from ta_london.geography import ENGLAND_CODE, LONDON_CODE, area_name_lookup
from ta_london.ingest.common import (
    clean_code,
    clean_label,
    column_index,
    find_header_row,
    parse_value,
    tidy,
)

SHEETS = ["TA1", "TA2", "TA3", "TA4c", "TA5", "TA6", "TA7", "TA8"]

_TYPE_PREFIX = {
    "bnb": "Households in B&Bs including shared annexes",
    "nightly_paid": "Households in nightly paid, privately managed accommodation or self-contained",
    "hostel": "Households in hostels",
    "private_sector": "Households in private sector accommodation",
    "la_ha_stock": "Households in LA/HA stock",
    "other": "Households in other TA",
}
_BANDS = {
    "less_than_6_months": "Less than 6 months",
    "6_to_12_months": "6 months to 1 year",
    "1_to_2_years": "1 to 2 years",
    "2_to_5_years": "2 to 5 years",
    "5_plus_years": "5 or more years",
}

# (cleaned header text, indicator, breakdown, unit)
SPECS: dict[str, list[tuple[str, str, str, str]]] = {
    "TA1": [
        ("Households in TA Total", "ta_households", "all", "households"),
        ("Households in area (thousands)", "households_in_area", "all", "thousand_households"),
        (
            "Households in TA Total (per thousand) Total",
            "ta_households_per_1000",
            "all",
            "per_1000_households",
        ),
        (
            "Households in TA with children Total",
            "ta_households_with_children",
            "all",
            "households",
        ),
        ("Children in TA Total", "ta_children", "all", "children"),
        (
            "Households in B&Bs including shared annexes With children",
            "ta_bnb_with_children",
            "all",
            "households",
        ),
        (
            "Households in B&Bs including shared annexes With children and resident "
            "more than 6 weeks",
            "ta_bnb_with_children_over_6_weeks",
            "all",
            "households",
        ),
        (
            "Households owed a TA duty in another LA Total",
            "ta_households_out_of_area",
            "all",
            "households",
        ),
        (
            "Households in duty owed, no accommodation secured Total",
            "ta_households_duty_owed_no_accommodation",
            "all",
            "households",
        ),
        (
            "Households in B&Bs including shared annexes Total",
            "ta_households_by_accommodation_type",
            "bnb",
            "households",
        ),
        (
            "Households in nightly paid, privately managed accommodation, self-contained Total",
            "ta_households_by_accommodation_type",
            "nightly_paid",
            "households",
        ),
        (
            "Households in hostels, including reception centres, emergency units and refuges Total",
            "ta_households_by_accommodation_type",
            "hostel",
            "households",
        ),
        (
            "Households in private sector accommodation Total",
            "ta_households_by_accommodation_type",
            "private_sector",
            "households",
        ),
        (
            "Households in LA or HA stock Total",
            "ta_households_by_accommodation_type",
            "la_ha_stock",
            "households",
        ),
        (
            "Households in any other type of TA, including private landlord and not known Total",
            "ta_households_by_accommodation_type",
            "other",
            "households",
        ),
    ],
    "TA2": [
        (
            "One adult with dependent child or children Male",
            "ta_households_by_composition",
            "one_adult_male_with_children",
            "households",
        ),
        (
            "One adult with dependent child or children Female",
            "ta_households_by_composition",
            "one_adult_female_with_children",
            "households",
        ),
        (
            "One adult with dependent child or children Sex not known or other",
            "ta_households_by_composition",
            "one_adult_other_sex_with_children",
            "households",
        ),
        (
            "Two adults with dependent child or children",
            "ta_households_by_composition",
            "two_adults_with_children",
            "households",
        ),
        (
            "Three or more adults with dependent child or children",
            "ta_households_by_composition",
            "three_plus_adults_with_children",
            "households",
        ),
        ("Adult only households Total", "ta_households_by_composition", "adult_only", "households"),
        (
            "All other household types/ Not known",
            "ta_households_by_composition",
            "other_or_not_known",
            "households",
        ),
    ],
    "TA3": [
        (
            "Households in TA Section 193 duty- priority need and unintentionally homeless",
            "ta_households_by_duty",
            "s193_main_duty",
            "households",
        ),
        (
            "Households in TA Interim- pending enquiries, intentionally homeless, review appeal, "
            "awaiting referral",
            "ta_households_by_duty",
            "interim",
            "households",
        ),
        (
            "Households in TA Section 189B power- emergency accommodation",
            "ta_households_by_duty",
            "s189b_emergency_accommodation",
            "households",
        ),
        (
            "Households in TA Duty ended, remains accommodated at end of quarter",
            "ta_households_by_duty",
            "duty_ended_still_accommodated",
            "households",
        ),
        (
            "Households in TA Duty not classifiable",
            "ta_households_by_duty",
            "not_classifiable",
            "households",
        ),
    ],
    "TA4c": [
        *(
            (f"{prefix} Total", "ta_families_by_accommodation_type", key, "households")
            for key, prefix in _TYPE_PREFIX.items()
        ),
        *(
            (f"{prefix} {band}", "ta_families_length_of_stay", f"{key}__{band_key}", "households")
            for key, prefix in _TYPE_PREFIX.items()
            for band_key, band in _BANDS.items()
        ),
    ],
    "TA5": [
        (label, "ta_households_by_age_of_main_applicant", key, "households")
        for label, key in [
            ("16 to 17", "16_to_17"),
            ("18 to 24", "18_to_24"),
            ("25 to 34", "25_to_34"),
            ("35 to 44", "35_to_44"),
            ("45 to 54", "45_to_54"),
            ("55 to 64", "55_to_64"),
            ("65 to 74", "65_to_74"),
            ("75 and over", "75_plus"),
            ("Not known", "not_known"),
        ]
    ],
    "TA6": [
        *(
            (label, "ta_households_by_ethnicity", key, "households")
            for label, key in [
                ("Asian or Asian British Total", "asian"),
                ("Black or African or Caribbean or Black British Total", "black"),
                ("Mixed or Multiple ethnic groups Total", "mixed"),
                ("Other ethnic group Total", "other_ethnic_group"),
                ("White Total", "white"),
                ("Not known", "not_known"),
            ]
        ),
        *(
            (label, "ta_households_by_ethnicity_detail", key, "households")
            for label, key in [
                ("Asian or Asian British Bangladeshi", "asian_bangladeshi"),
                ("Asian or Asian British Chinese", "asian_chinese"),
                ("Asian or Asian British Indian", "asian_indian"),
                ("Asian or Asian British Pakistani", "asian_pakistani"),
                ("Asian or Asian British Other", "asian_other"),
                ("Black or African or Caribbean or Black British African", "black_african"),
                ("Black or African or Caribbean or Black British Caribbean", "black_caribbean"),
                ("Black or African or Caribbean or Black British Other", "black_other"),
                (
                    "Mixed or Multiple ethnic groups White and Black African",
                    "mixed_white_black_african",
                ),
                ("Mixed or Multiple ethnic groups White and Asian", "mixed_white_asian"),
                (
                    "Mixed or Multiple ethnic groups White and Black Caribbean",
                    "mixed_white_black_caribbean",
                ),
                ("Mixed or Multiple ethnic groups Other", "mixed_other"),
                ("Other ethnic group Arab", "other_arab"),
                ("Other ethnic group Any other ethnic group", "other_any_other"),
                (
                    "White English or Welsh or Scottish or Northern Irish or British",
                    "white_british",
                ),
                ("White Irish", "white_irish"),
                ("White Gypsy or Irish Traveller", "white_gypsy_irish_traveller"),
                ("White Other", "white_other"),
                ("Not known", "not_known"),
            ]
        ),
    ],
    "TA7": [
        (f"{label} {stat} (days)", f"ta_length_of_stay_{stat.lower()}_days", key, "days")
        for stat in ("Median", "Mean")
        for label, key in [
            ("B&B or shared annex", "bnb"),
            ("Hostel or refuge", "hostel"),
            ("LA/HA stock", "la_ha_stock"),
            ("Nightly paid, privately managed accommodation, self-contained", "nightly_paid"),
            ("Other or not known", "other_or_not_known"),
            ("Own arrangements", "own_arrangements"),
            ("Private sector accommodation", "private_sector"),
        ]
    ],
    "TA8": [
        ("People aged under 18 Total", "ta_children_under_18", "all", "children"),
        *((str(a), "ta_children_by_age", f"age_{a}", "children") for a in range(18)),
    ],
}

# TA7 reports 0 days where a type has no households; an average of 0 days is not a real
# measurement, so it is treated as missing (not applicable).
_ZERO_IS_MISSING = {"ta_length_of_stay_median_days", "ta_length_of_stay_mean_days"}

_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


def snapshot_period(ta1_df: pd.DataFrame) -> tuple[str, date]:
    """Period label and end date from TA1's title, e.g. 'as at 31 March 2026' -> 2026-Q1."""
    title = " ".join(str(ta1_df.iloc[0, 0]).split())
    m = re.search(r"as at (\d{1,2}) ([A-Za-z]+) (\d{4})", title)
    if not m or m.group(2) not in _MONTHS:
        raise ValueError(f"Cannot read the snapshot date from the TA1 title: {title!r}")
    end = date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    return f"{end.year}-Q{(end.month - 1) // 3 + 1}", end


def _area_rows(df: pd.DataFrame, header_row: int, borough_codes: set[str]) -> pd.DataFrame:
    body = df.iloc[header_row + 1 :].copy()
    body.index = body.iloc[:, 0].map(clean_code)
    keep = body.index.isin(borough_codes | {LONDON_CODE, ENGLAND_CODE})
    body = body[keep]
    # London appears twice in the published tables. Drop exact duplicates, fail on conflicts.
    dup = body.index.duplicated(keep=False)
    if dup.any() and body[dup].astype(str).drop_duplicates().index.duplicated().any():
        raise ValueError("Duplicate area rows with different values")
    return body[~body.index.duplicated(keep="first")]


def parse_ta_sheets(
    sheets: dict[str, pd.DataFrame], source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    """Parse the TA sheets (read with header=None) into tidy rows."""
    names = names or area_name_lookup()
    borough_codes = {c for c in names if c.startswith("E09")}
    period, period_end = snapshot_period(sheets["TA1"])
    records: list[dict] = []
    for sheet, specs in SPECS.items():
        df = sheets[sheet]
        h = find_header_row(df, "Organisation")
        labels = [clean_label(v) for v in df.iloc[h]]
        rows = _area_rows(df, h, borough_codes)
        for label, indicator, breakdown, unit in specs:
            col = column_index(labels, label, sheet)
            for code, raw in zip(rows.index, rows.iloc[:, col], strict=True):
                value, status = parse_value(raw)
                if indicator in _ZERO_IS_MISSING and status == "ok" and value == 0:
                    value, status = math.nan, "missing"
                records.append(
                    {
                        "area_code": code,
                        "area_name": names[code],
                        "period": period,
                        "period_type": "quarter_end",
                        "period_end": period_end,
                        "indicator": indicator,
                        "breakdown": breakdown,
                        "value": value,
                        "value_status": status,
                        "unit": unit,
                        "source_id": source_id,
                    }
                )
    return tidy(records)


def load(path, source_id: str, names: dict[str, str] | None = None) -> pd.DataFrame:
    sheets = pd.read_excel(path, engine="odf", sheet_name=SHEETS, header=None)
    return parse_ta_sheets(sheets, source_id, names)

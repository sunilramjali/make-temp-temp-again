"""MHCLG Live Table 600: households on local authority housing registers (waiting lists).

Sheet Local_Authority_Data: one row per local authority, one column per year (the year is the
31 March reference date; up to 2018 the reference date was 1 April, per table note 3).
Values MHCLG imputed are listed in the Imputations sheet and are flagged 'estimated' here.
"""

import math
from datetime import date

import pandas as pd

from ta_london.geography import area_name_lookup
from ta_london.ingest.common import clean_code, find_header_row, parse_value, tidy

SHEETS = ["Local_Authority_Data", "Imputations"]
FIRST_YEAR = 2012  # table sources: 2012 onwards = Local Authority Housing Statistics


def reference_date(year: int) -> date:
    return date(year, 4, 1) if year <= 2018 else date(year, 3, 31)


def _imputed(imputations_df: pd.DataFrame) -> set[tuple[str, int]]:
    h = find_header_row(imputations_df, "Local authority")
    return {
        (str(name).strip(), int(year))
        for name, year in zip(
            imputations_df.iloc[h + 1 :, 0], imputations_df.iloc[h + 1 :, 1], strict=True
        )
        if not (isinstance(name, float) and math.isnan(name))
    }


def parse_lt600(
    la_df: pd.DataFrame,
    imputations_df: pd.DataFrame,
    source_id: str,
    names: dict[str, str] | None = None,
) -> pd.DataFrame:
    names = names or area_name_lookup()
    h = find_header_row(la_df, "Local authority code")
    header = [str(v).strip().removesuffix(".0") for v in la_df.iloc[h]]
    year_cols = {int(c): i for i, c in enumerate(header) if c.isdigit() and int(c) >= FIRST_YEAR}
    if not year_cols:
        raise ValueError("Live Table 600: no year columns found")
    name_col = header.index("Local authority")
    imputed = _imputed(imputations_df)

    records = []
    for _, row in la_df.iloc[h + 1 :].iterrows():
        code = clean_code(row.iloc[0])
        if code not in names or not code.startswith("E09"):
            continue
        la_name = str(row.iloc[name_col]).strip()
        for year, col in sorted(year_cols.items()):
            value, status = parse_value(row.iloc[col])
            if status == "ok" and (la_name, year) in imputed:
                status = "estimated"
            end = reference_date(year)
            records.append(
                {
                    "area_code": code,
                    "area_name": names[code],
                    "period": end.isoformat(),
                    "period_type": "snapshot",
                    "period_end": end,
                    "indicator": "housing_register_households",
                    "breakdown": "all",
                    "value": value,
                    "value_status": status,
                    "unit": "households",
                    "source_id": source_id,
                }
            )
    return tidy(records)


def load(path, source_id: str, names: dict[str, str] | None = None) -> pd.DataFrame:
    sheets = pd.read_excel(path, engine="odf", sheet_name=SHEETS, header=None)
    return parse_lt600(sheets["Local_Authority_Data"], sheets["Imputations"], source_id, names)

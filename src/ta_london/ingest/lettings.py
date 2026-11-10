"""CORE social housing lettings summary tables (tenancies), 2024-25 release.

Table 1d: new social housing lettings by local authority, 2009/10 to 2024/25 (E codes from
2011/12). Table 1e: re-lets, rents and churn for the latest year only.

Data is unweighted and as reported (table note 9). Some councils did not submit CORE data in the
latest year (note 10), so their figures are under-counts. Those councils are read from note 10 on
the Notes sheet and their CORE-based rows for that year get value_status 'incomplete'.
"""

import re
from datetime import date

import pandas as pd

from ta_london.geography import area_name_lookup
from ta_london.ingest.common import (
    clean_code,
    clean_label,
    column_index,
    find_header_row,
    parse_value,
    slug,
    tidy,
)

SHEETS = ["Notes", "Table_1d", "Table_1e"]

# Rows that rest on CORE lettings returns. Stock (regulator / LT116) and market rent (ONS) don't.
INCOMPLETE_INDICATORS = {
    "social_lettings_total",
    "social_lettings_by_type",
    "social_relets",
    "social_relet_rate",
    "social_relet_rent_weekly",
    "social_rent_pct_of_market_rent",
}
_NOTE_10 = re.compile(
    r"did not submit CORE data in (\d{4}/\d{2}).*?These were:\s*(.+?)\.", re.DOTALL
)

_LEAF_LABELS = [
    f"{tenure} {need} {landlord}"
    for tenure in ("SR", "AR", "IR")
    for need in ("General Needs", "Supported Housing")
    for landlord in ("LA", "PRP")
]

_1E_SPECS = [
    (
        "Average weekly rent for social housing re-lets (£)",
        "social_relet_rent_weekly",
        "gbp_per_week",
    ),
    ("Average weekly market rent (£)", "market_rent_weekly", "gbp_per_week"),
    (
        "Average weekly rent for a re-let as a proportion of market rent (%)",
        "social_rent_pct_of_market_rent",
        "percent",
    ),
    ("New social housing re-lets", "social_relets", "lettings"),
    ("Total social stock at 1 April", "social_stock_1_april", "homes"),
    ("Proportion of social stock re-let (%)", "social_relet_rate", "percent"),
]


def _financial_year(label: str) -> tuple[str, date]:
    m = re.fullmatch(r"(\d{4})/(\d{2})", label.strip())
    if not m:
        raise ValueError(f"Unexpected financial year label {label!r}")
    start = int(m.group(1))
    return f"{start}-{m.group(2)}", date(start + 1, 3, 31)


def parse_table_1d(
    df: pd.DataFrame, source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    names = names or area_name_lookup()
    h = find_header_row(df, "Financial year")
    labels = [clean_label(v) for v in df.iloc[h]]
    year_col = column_index(labels, "Financial year", "Table_1d")
    code_col = column_index(labels, "LA Code at time of letting", "Table_1d")
    total_col = column_index(labels, "Total", "Table_1d")
    leaf_cols = {label: column_index(labels, label, "Table_1d") for label in _LEAF_LABELS}

    records = []
    for _, row in df.iloc[h + 1 :].iterrows():
        code = clean_code(row.iloc[code_col])
        if code not in names or not code.startswith("E09"):
            continue
        period, end = _financial_year(str(row.iloc[year_col]))
        parts = [("social_lettings_total", "all", total_col)] + [
            ("social_lettings_by_type", slug(label), col) for label, col in leaf_cols.items()
        ]
        for indicator, breakdown, col in parts:
            value, status = parse_value(row.iloc[col])
            records.append(
                {
                    "area_code": code,
                    "area_name": names[code],
                    "period": period,
                    "period_type": "financial_year",
                    "period_end": end,
                    "indicator": indicator,
                    "breakdown": breakdown,
                    "value": value,
                    "value_status": status,
                    "unit": "lettings",
                    "source_id": source_id,
                }
            )
    return tidy(records)


def table_1e_period(df: pd.DataFrame) -> tuple[str, date]:
    title = " ".join(str(df.iloc[0, 0]).split())
    m = re.search(r"(\d{4}/\d{2})", title)
    if not m:
        raise ValueError(f"Cannot read the financial year from the Table 1e title: {title!r}")
    return _financial_year(m.group(1))


def parse_table_1e(
    df: pd.DataFrame, source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    names = names or area_name_lookup()
    period, end = table_1e_period(df)
    h = find_header_row(df, "Region Code")
    labels = [clean_label(v) for v in df.iloc[h]]
    code_col = column_index(labels, "LA Code at time of letting", "Table_1e")
    cols = [(column_index(labels, label, "Table_1e"), ind, unit) for label, ind, unit in _1E_SPECS]

    records = []
    for _, row in df.iloc[h + 1 :].iterrows():
        code = clean_code(row.iloc[code_col])
        if code not in names or not code.startswith("E09"):
            continue
        for col, indicator, unit in cols:
            value, status = parse_value(row.iloc[col])
            records.append(
                {
                    "area_code": code,
                    "area_name": names[code],
                    "period": period,
                    "period_type": "financial_year",
                    "period_end": end,
                    "indicator": indicator,
                    "breakdown": "all",
                    "value": value,
                    "value_status": status,
                    "unit": unit,
                    "source_id": source_id,
                }
            )
    return tidy(records)


def non_submitters(
    notes: pd.DataFrame, names: dict[str, str] | None = None
) -> tuple[str, set[str]]:
    """(period, London area codes) of councils that note 10 says did not submit CORE data.

    Fails loudly if the note can't be found, since the note number or wording may change
    between releases. Names outside London are ignored.
    """
    names = names or area_name_lookup()
    # The note number and its text may be in separate columns, so join each row's cells.
    rows = [
        " ".join(" ".join(str(v) for v in row if pd.notna(v)).split())
        for row in notes.itertuples(index=False)
    ]
    note = next((r for r in rows if r.startswith("[note 10]")), None)
    m = _NOTE_10.search(note or "")
    if not m:
        raise ValueError("Cannot find the CORE non-submission list in note 10 of the Notes sheet")
    period, _ = _financial_year(m.group(1))
    # Match whole names between list separators, so "Barking and Dagenham" isn't split on "and".
    text = m.group(2)
    codes = {
        code
        for code, name in names.items()
        if re.search(rf"(?:^|,\s*|\band\s+){re.escape(name)}(?:\s*,|\s+and\b|$)", text, re.I)
    }
    return period, codes


def mark_incomplete(df: pd.DataFrame, period: str, codes: set[str]) -> pd.DataFrame:
    """Set value_status 'incomplete' on CORE-based rows for non-submitting councils."""
    hit = (
        df["area_code"].isin(codes)
        & df["period"].eq(period)
        & df["indicator"].isin(INCOMPLETE_INDICATORS)
        & df["value"].notna()
    )
    return df.assign(value_status=df["value_status"].where(~hit, "incomplete"))


def load(path, source_id: str, names: dict[str, str] | None = None) -> pd.DataFrame:
    names = names or area_name_lookup()
    sheets = pd.read_excel(path, engine="odf", sheet_name=SHEETS, header=None)
    df = pd.concat(
        [
            parse_table_1d(sheets["Table_1d"], source_id, names),
            parse_table_1e(sheets["Table_1e"], source_id, names),
        ],
        ignore_index=True,
    )
    period, codes = non_submitters(sheets["Notes"], names)
    return mark_incomplete(df, period, codes)

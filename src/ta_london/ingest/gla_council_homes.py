"""GLA housing statistics: Council Homes delivered via GLA programmes (Table 2, by borough).

Starts on site and completions by financial year. Only homes in GLA programmes are counted; the
GLA notes say other council homes are reported in MHCLG statistics, so this is not total supply.
The first year runs from September 2018. The latest year is partial (to the date in the title)
and is left out. The 'Multiple London Boroughs' row is not a borough and is left out.
Boroughs are matched to ONS codes by exact ONS name.
"""

import re
from datetime import date

import pandas as pd

from ta_london.geography import area_name_lookup
from ta_london.ingest.common import parse_value, tidy

SHEET = "GLA Council Homes LA "  # trailing space is in the published sheet name
_NOT_BOROUGH = {"Multiple London Boroughs", "Total"}


def _cells(df: pd.DataFrame) -> list[list[str]]:
    return [
        ["" if pd.isna(v) else str(v).strip() for v in row] for row in df.itertuples(index=False)
    ]


def parse_table_2(
    df: pd.DataFrame, source_id: str, names: dict[str, str] | None = None
) -> pd.DataFrame:
    names = names or area_name_lookup()
    code_by_name = {n: c for c, n in names.items() if c.startswith("E09")}
    rows = _cells(df)
    title = " ".join(rows[1]).strip()
    m = re.search(r"To end of (\w+) (\d{4})", title)
    if not m:
        raise ValueError(f"GLA Table 2: cannot read the 'To end of' date from {title!r}")
    header_i = next(i for i, r in enumerate(rows) if "Local Authority" in r)
    header = rows[header_i]
    blocks = [i for i, v in enumerate(header) if v == "Local Authority"]
    if len(blocks) != 2:
        raise ValueError("GLA Table 2: expected a starts block and a completions block")
    group_row = rows[header_i - 2]
    kinds = []
    for b in blocks:
        label = " ".join(group_row[max(0, b - 1) : b + 2]).lower()
        kinds.append("started" if "start" in label else "completed")
    if sorted(kinds) != ["completed", "started"]:
        raise ValueError(f"GLA Table 2: could not identify starts and completions blocks: {kinds}")

    records = []
    for block_start, kind in zip(blocks, kinds, strict=True):
        year_cols = []
        for j in range(block_start + 1, len(header)):
            fy = re.match(r"(\d{4})-(\d{2})", header[j])
            if not fy:
                break
            year_cols.append((j, int(fy.group(1)), fy.group(2)))
        latest = max(y for _, y, _ in year_cols)
        for r in rows[header_i + 1 :]:
            name = r[block_start]
            if not name or name in _NOT_BOROUGH or name.startswith("Multiple"):
                continue
            if name not in code_by_name:
                raise ValueError(f"GLA Table 2: borough name {name!r} not in the ONS lookup")
            code = code_by_name[name]
            for j, start_year, end_yy in year_cols:
                if start_year == latest:
                    continue  # partial year (to the 'To end of' date)
                value, status = parse_value(r[j] if r[j] != "" else None)
                records.append(
                    {
                        "area_code": code,
                        "area_name": names[code],
                        "period": f"{start_year}-{end_yy}",
                        "period_type": "financial_year",
                        "period_end": date(start_year + 1, 3, 31),
                        "indicator": f"council_homes_{kind}_gla",
                        "breakdown": "all",
                        "value": value,
                        "value_status": status,
                        "unit": "homes",
                        "source_id": source_id,
                    }
                )
    out = tidy(records)
    for ind in ("council_homes_started_gla", "council_homes_completed_gla"):
        n = out[out.indicator == ind]["area_code"].nunique()
        if n != 33:
            raise ValueError(f"GLA Table 2: {ind} has {n} boroughs, expected 33")
    return out


def load(path, source_id: str, names: dict[str, str] | None = None) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=SHEET, header=None, engine="openpyxl")
    return parse_table_2(df, source_id, names)

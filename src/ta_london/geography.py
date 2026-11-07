"""London borough lookup (33 boroughs incl. City of London).

The lookup is derived from MHCLG Live Table 600, which carries the ONS name (LAD24NM) and code
for every local authority, so no code is typed from memory.
"""

import pandas as pd

from ta_london.ingest.common import clean_code, find_header_row
from ta_london.paths import REFERENCE

BOROUGHS_CSV = REFERENCE / "london_boroughs.csv"

LONDON_CODE = "E12000007"
ENGLAND_CODE = "E92000001"
NEWHAM_CODE = "E09000025"
AREA_NAMES = {LONDON_CODE: "London", ENGLAND_CODE: "England"}


def build_boroughs_from_lt600(local_authority_df: pd.DataFrame) -> pd.DataFrame:
    """The 33 London boroughs (E09 codes) from Live Table 600's Local_Authority_Data sheet."""
    h = find_header_row(local_authority_df, "Local authority code")
    header = [str(v).strip() for v in local_authority_df.iloc[h]]
    code_col, name_col = header.index("Local authority code"), header.index("LAD24NM")
    body = local_authority_df.iloc[h + 1 :]
    codes = body.iloc[:, code_col].map(clean_code)
    out = pd.DataFrame(
        {
            "area_code": codes[codes.str.startswith("E09")],
            "area_name": body.iloc[:, name_col][codes.str.startswith("E09")].str.strip(),
        }
    )
    out = out.drop_duplicates().sort_values("area_code").reset_index(drop=True)
    expected = {f"E09{n:06d}" for n in range(1, 34)}
    if len(out) != 33 or set(out["area_code"]) != expected:
        raise ValueError(
            f"Expected the 33 London boroughs E09000001-E09000033, got {len(out)} rows"
        )
    return out


def write_boroughs(df: pd.DataFrame, path=BOROUGHS_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_boroughs(path=BOROUGHS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    if list(df.columns) != ["area_code", "area_name"] or len(df) != 33:
        raise ValueError(f"{path} should have columns area_code, area_name and 33 rows")
    return df


def area_name_lookup(path=BOROUGHS_CSV) -> dict[str, str]:
    names = dict(zip(*load_boroughs(path).T.values, strict=True))
    return {**names, **AREA_NAMES}

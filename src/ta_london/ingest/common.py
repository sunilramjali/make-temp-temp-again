"""Helpers shared by the loaders: header cleaning, value parsing, tidy row building."""

import math
import re

import pandas as pd

from ta_london.schema import COLUMNS

_NOTE_RE = re.compile(r"\s*,?\s*\[note \d+\]")

# MHCLG markers. [c] = data suppressed, [x] = missing/not available, [z] = not applicable.
MARKER_STATUS = {"[c]": "suppressed", "[x]": "missing", "[z]": "missing"}


def clean_label(raw) -> str:
    """Column header text with note references and extra whitespace removed."""
    return " ".join(_NOTE_RE.sub("", str(raw)).split())


def clean_code(raw) -> str:
    return str(raw).strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_value(raw) -> tuple[float, str]:
    """Return (value, status). Markers become NaN plus a reason; anything unknown raises."""
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return math.nan, "missing"
    if isinstance(raw, str):
        text = raw.strip()
        if text in MARKER_STATUS:
            return math.nan, MARKER_STATUS[text]
        try:
            return float(text.replace(",", "")), "ok"
        except ValueError:
            raise ValueError(f"Unrecognised cell value {raw!r}") from None
    return float(raw), "ok"


def find_header_row(df: pd.DataFrame, first_cell_prefix: str, max_rows: int = 15) -> int:
    for i in range(min(max_rows, len(df))):
        if str(df.iloc[i, 0]).strip().startswith(first_cell_prefix):
            return i
    raise ValueError(f"No header row starting {first_cell_prefix!r} in the first {max_rows} rows")


def column_index(labels: list[str], wanted: str, sheet: str) -> int:
    """Position of a column by its cleaned header text. Fails loudly if absent or ambiguous."""
    hits = [i for i, label in enumerate(labels) if label == wanted]
    if len(hits) != 1:
        raise ValueError(
            f"Sheet {sheet}: expected exactly one column labelled {wanted!r}, found {len(hits)}. "
            "The release layout may have changed."
        )
    return hits[0]


def tidy(records: list[dict]) -> pd.DataFrame:
    """Build a DataFrame in schema order with the right dtypes, sorted for determinism."""
    df = pd.DataFrame.from_records(records, columns=COLUMNS)
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["value"] = df["value"].astype(float)
    return df.sort_values(["area_code", "indicator", "breakdown", "period_end"]).reset_index(
        drop=True
    )

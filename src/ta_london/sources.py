"""Load and check the dataset register, data/sources.csv."""

import pandas as pd

from ta_london.paths import SOURCES_CSV

REQUIRED_COLUMNS = [
    "source_id",
    "title",
    "publisher",
    "url",
    "geography",
    "reference_period",
    "definition_notes",
    "raw_file",
    "date_accessed",
    "methodology_step",
    "notes",
]


def load_sources(path=SOURCES_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    dupes = df.loc[df["source_id"].duplicated(), "source_id"].tolist()
    if dupes:
        raise ValueError(f"Duplicate source_id in {path}: {dupes}")
    return df


def assert_registered(source_ids, path=SOURCES_CSV) -> None:
    """Raise if any source_id is not in the register."""
    registered = set(load_sources(path)["source_id"])
    unknown = sorted(set(source_ids) - registered)
    if unknown:
        raise ValueError(f"source_id not registered in sources.csv: {unknown}")

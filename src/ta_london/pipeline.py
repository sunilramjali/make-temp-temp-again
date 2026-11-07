"""Run all ingest -> validate -> indicators -> write parquet steps.

    uv run python -m ta_london.pipeline

Reads only from data/raw/. Writes the borough reference to data/reference/, one interim table per
source to data/interim/, and the tidy table to data/processed/indicators.parquet. Deterministic:
deleting interim/ and processed/ and re-running gives identical output.
"""

import pandas as pd

from ta_london import geography, indicators, schema, sources
from ta_london.ingest import gla_council_homes, lettings, mhclg_ta, trust_for_london, waiting_list
from ta_london.paths import INTERIM, PROCESSED, RAW

LT600 = RAW / "mhclg" / "Live_Table_600.ods"
TA_TABLES = RAW / "mhclg" / "Statutory_Homelessness_Detailed_Local_Authority_Data_202603.ods"
CORE_TENANCIES = (
    RAW / "mhclg" / "Social_Housing_Lettings_in_England__Tenancies_Summary_Tables__2024-25.ods"
)

T87 = RAW / "trust_for_london" / "T87_EqlYvkV.csv"
T88 = RAW / "trust_for_london" / "T88_55WCaNF.csv"
GLA_HOMES = RAW / "gla" / "GLA stats - council homes_Q1_2026-27.xlsx"

TA_SOURCE = "mhclg_la_detailed_2026q1"
T87_SOURCE = "tfl_lpp_t87_2026"
T88_SOURCE = "tfl_lpp_t88_2026"
GLA_SOURCE = "gla_council_homes_2026q1"
KEY = ["area_code", "period", "period_type", "indicator", "breakdown"]
LT600_SOURCE = "mhclg_lt600_2025"
CORE_SOURCE = "mhclg_core_tenancies_2425"
OUTPUT = PROCESSED / "indicators.parquet"


def _write(df: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def drop_overlap(primary: pd.DataFrame, secondary: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Rows of `secondary` not already in `primary`. Overlapping values must agree within
    `tolerance` (e.g. rounding to the nearest 10); otherwise the sources disagree and we stop."""
    both = secondary.merge(primary[[*KEY, "value"]], on=KEY, suffixes=("", "_primary"))
    gap = (both["value"] - both["value_primary"]).abs()
    if (gap > tolerance).any():
        bad = both.loc[gap > tolerance, [*KEY, "value", "value_primary"]]
        raise ValueError(f"Sources disagree beyond rounding:\n{bad}")
    keys = set(map(tuple, both[KEY].values))
    return secondary[[tuple(r) not in keys for r in secondary[KEY].values]]


def assert_unique(df: pd.DataFrame) -> None:
    dup = df.duplicated(KEY, keep=False)
    if dup.any():
        raise ValueError(f"Duplicate rows for the same measure:\n{df.loc[dup, KEY].head(10)}")


def run() -> pd.DataFrame:
    for p in (LT600, TA_TABLES, CORE_TENANCIES, T87, T88, GLA_HOMES):
        if not p.exists():
            raise FileNotFoundError(f"Raw file missing: {p}")

    print("Borough reference from Live Table 600 ...")
    la = pd.read_excel(LT600, engine="odf", sheet_name="Local_Authority_Data", header=None)
    geography.write_boroughs(geography.build_boroughs_from_lt600(la))
    names = geography.area_name_lookup()

    parts = {}
    print("Waiting list (Live Table 600) ...")
    parts["housing_register"] = waiting_list.load(LT600, LT600_SOURCE, names)
    print("Temporary accommodation (TA1-TA8) ...")
    parts["ta_detailed"] = mhclg_ta.load(TA_TABLES, TA_SOURCE, names)
    print("Social lettings (CORE Tables 1d, 1e) ...")
    parts["core_lettings"] = lettings.load(CORE_TENANCIES, CORE_SOURCE, names)
    print("Trust for London T87 (London TA 2002-2025) and T88 (boroughs, 2025) ...")
    t87 = trust_for_london.load_t87(T87, T87_SOURCE, names)
    t88 = trust_for_london.load_t88(T88, T88_SOURCE, names)
    # London 2025 appears in both; T87 is unrounded, T88 rounded to the nearest 10.
    parts["tfl_t87"] = t87
    parts["tfl_t88"] = drop_overlap(t87, t88, tolerance=10)
    print("GLA council homes (starts and completions) ...")
    parts["gla_council_homes"] = gla_council_homes.load(GLA_HOMES, GLA_SOURCE, names)
    for name, df in parts.items():
        _write(df, INTERIM / f"{name}.parquet")

    df = pd.concat(parts.values(), ignore_index=True)
    df = indicators.add_ratios(indicators.add_shares(df))
    assert_unique(df)
    sources.assert_registered(df["source_id"].unique())
    indicators.assert_in_dictionary(df)
    df = schema.validate(df)
    _write(df, OUTPUT)
    print(f"Wrote {len(df):,} rows, {df['indicator'].nunique()} indicators to {OUTPUT}")
    return df


def main() -> None:
    run()


if __name__ == "__main__":
    main()

"""Run all ingest -> validate -> indicators -> write parquet steps.

    uv run python -m ta_london.pipeline

Reads only from data/raw/. Writes the borough reference to data/reference/, one interim table per
source to data/interim/, and the tidy table to data/processed/indicators.parquet. Deterministic:
deleting interim/ and processed/ and re-running gives identical output.
"""

import pandas as pd

from ta_london import geography, indicators, schema, sources
from ta_london.ingest import lettings, mhclg_ta, waiting_list
from ta_london.paths import INTERIM, PROCESSED, RAW

LT600 = RAW / "mhclg" / "Live_Table_600.ods"
TA_TABLES = RAW / "mhclg" / "Statutory_Homelessness_Detailed_Local_Authority_Data_202603.ods"
CORE_TENANCIES = (
    RAW / "mhclg" / "Social_Housing_Lettings_in_England__Tenancies_Summary_Tables__2024-25.ods"
)

TA_SOURCE = "mhclg_la_detailed_2026q1"
LT600_SOURCE = "mhclg_lt600_2025"
CORE_SOURCE = "mhclg_core_tenancies_2425"
OUTPUT = PROCESSED / "indicators.parquet"


def _write(df: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def run() -> pd.DataFrame:
    for p in (LT600, TA_TABLES, CORE_TENANCIES):
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
    for name, df in parts.items():
        _write(df, INTERIM / f"{name}.parquet")

    df = pd.concat(parts.values(), ignore_index=True)
    df = indicators.add_ratios(indicators.add_shares(df))
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

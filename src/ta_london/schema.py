"""Pandera schema for the tidy indicators table (data/processed/indicators.parquet)."""

import pandera.pandas as pa

COLUMNS = [
    "area_code",
    "area_name",
    "period",
    "period_type",
    "period_end",
    "indicator",
    "breakdown",
    "value",
    "value_status",
    "unit",
    "source_id",
]

# quarter_end: count on the last day of a quarter. quarter: flow during a quarter (e.g. exits).
# calendar_year_average: average of the four quarters of a calendar year (Trust for London).
PERIOD_TYPES = ["quarter_end", "quarter", "financial_year", "snapshot", "calendar_year_average"]
VALUE_STATUSES = ["ok", "suppressed", "missing", "estimated"]
AREA_CODE_PATTERN = r"^(E0[6-9]\d{6}|E1[0-2]\d{6}|E92000001)$"

tidy_schema = pa.DataFrameSchema(
    {
        "area_code": pa.Column(str, pa.Check.str_matches(AREA_CODE_PATTERN)),
        "area_name": pa.Column(str),
        "period": pa.Column(str),
        "period_type": pa.Column(str, pa.Check.isin(PERIOD_TYPES)),
        "period_end": pa.Column("datetime64[ns]"),
        "indicator": pa.Column(str, pa.Check.str_matches(r"^[a-z][a-z0-9_]*$")),
        "breakdown": pa.Column(str),
        "value": pa.Column(float, nullable=True),
        "value_status": pa.Column(str, pa.Check.isin(VALUE_STATUSES)),
        "unit": pa.Column(str),
        "source_id": pa.Column(str),
    },
    checks=[
        # NaN must carry a reason; a real value can't be marked suppressed/missing.
        pa.Check(
            lambda df: df["value"].isna() == df["value_status"].isin(["suppressed", "missing"]),
            error="value is NaN exactly when value_status is suppressed or missing",
        ),
    ],
    strict=True,
    ordered=True,
)


def validate(df):
    """Validate a tidy DataFrame, raising pandera.errors.SchemaError(s) if it is invalid."""
    return tidy_schema.validate(df[COLUMNS] if set(COLUMNS) <= set(df.columns) else df, lazy=True)

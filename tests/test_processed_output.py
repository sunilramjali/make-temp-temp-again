"""Checks on the real pipeline output. Skipped if the pipeline has not been run."""

import pandas as pd
import pytest

from ta_london.paths import PROCESSED

PARQUET = PROCESSED / "indicators.parquet"
pytestmark = pytest.mark.skipif(not PARQUET.exists(), reason="run the pipeline first")


@pytest.fixture(scope="module")
def df():
    return pd.read_parquet(PARQUET)


def one(df, area, indicator, breakdown="all", period=None):
    r = df[(df.area_code == area) & (df.indicator == indicator) & (df.breakdown == breakdown)]
    if period:
        r = r[r.period == period]
    assert len(r) == 1, (area, indicator, breakdown, period, len(r))
    return r.iloc[0]


def test_all_33_boroughs_present_for_key_indicators(df):
    for indicator in ("ta_households", "housing_register_households", "social_lettings_total"):
        boroughs = df[(df.indicator == indicator) & df.area_code.str.startswith("E09")]
        assert boroughs.area_code.nunique() == 33, indicator


def test_waiting_list_has_at_least_8_periods(df):
    sub = df[(df.indicator == "housing_register_households") & (df.area_code == "E09000025")]
    assert sub.period.nunique() >= 8


def test_newham_ta_spot_checks_against_source_file(df):
    assert one(df, "E09000025", "ta_households")["value"] == 7561
    assert one(df, "E09000025", "ta_households_with_children")["value"] == 5453
    assert (
        one(df, "E09000025", "ta_households_by_composition", "two_adults_with_children")["value"]
        == 1915
    )
    assert (
        one(df, "E09000025", "ta_families_length_of_stay", "nightly_paid__5_plus_years")["value"]
        == 843
    )


def test_newham_other_sources_spot_checks(df):
    assert (
        one(df, "E09000025", "housing_register_households", period="2025-03-31")["value"] == 41223
    )
    assert one(df, "E09000025", "social_lettings_total", period="2024-25")["value"] == 711


def test_ethnicity_not_known_is_kept_visible(df):
    nk = one(df, "E09000025", "ta_households_by_ethnicity", "not_known")
    assert nk["value"] == 2227
    share = one(df, "E09000025", "ta_households_by_ethnicity_share", "not_known")["value"]
    assert round(share, 1) == 29.5


def test_suppressed_values_are_nan_never_zero(df):
    bad = df[df.value_status.isin(["suppressed", "missing"])]
    assert len(bad) > 0 and bad.value.isna().all()
    assert df[df.value_status.isin(["ok", "estimated"])].value.notna().all()
    # [c] markers in the source: several boroughs have small-count length-of-stay cells
    assert set(df[df.value_status == "suppressed"].indicator) >= {"ta_families_length_of_stay"}


def test_imputed_waiting_list_values_flagged(df):
    r = df[(df.indicator == "housing_register_households") & (df.value_status == "estimated")]
    assert {"Croydon", "Waltham Forest", "Enfield", "Sutton"} <= set(r.area_name)


def test_every_source_id_is_registered(df):
    from ta_london.sources import assert_registered

    assert_registered(df.source_id.unique())


def test_out_of_area_share_is_derived(df):
    r = one(df, "E09000025", "ta_households_out_of_area_share")
    assert round(r["value"], 1) == 42.0 and r["unit"] == "percent"

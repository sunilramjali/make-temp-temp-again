import math

import pandas as pd

from ta_london import indicators
from ta_london.ingest import lettings, mhclg_ta
from ta_london.schema import COLUMNS, validate


def rows(indicator, parts, area="E09000025", unit="households"):
    out = []
    for breakdown, (value, status) in parts.items():
        out.append(
            dict(
                area_code=area,
                area_name="Newham",
                period="2026-Q1",
                period_type="quarter_end",
                period_end=pd.Timestamp("2026-03-31"),
                indicator=indicator,
                breakdown=breakdown,
                value=value,
                value_status=status,
                unit=unit,
                source_id="s",
            )
        )
    return pd.DataFrame(out, columns=COLUMNS)


def share(df, indicator, breakdown):
    r = df[(df.indicator == indicator) & (df.breakdown == breakdown)]
    assert len(r) == 1
    return r.iloc[0]


def test_shares_partition_to_100():
    df = rows("ta_households_by_duty", {"a": (75, "ok"), "b": (25, "ok")})
    out = indicators.add_shares(df)
    assert share(out, "ta_households_by_duty_share", "a")["value"] == 75
    assert share(out, "ta_households_by_duty_share", "b")["unit"] == "percent"
    validate(out)


def test_share_is_nan_if_any_part_suppressed():
    df = rows("ta_households_by_duty", {"a": (75, "ok"), "b": (math.nan, "suppressed")})
    out = indicators.add_shares(df)
    r = share(out, "ta_households_by_duty_share", "a")
    assert math.isnan(r["value"]) and r["value_status"] == "suppressed"
    validate(out)


def test_zero_total_gives_missing_share_not_a_division_error():
    df = rows("ta_households_by_duty", {"a": (0, "ok"), "b": (0, "ok")})
    out = indicators.add_shares(df)
    r = share(out, "ta_households_by_duty_share", "a")
    assert math.isnan(r["value"]) and r["value_status"] == "missing"


def test_length_of_stay_shares_are_within_each_type():
    df = rows(
        "ta_families_length_of_stay",
        {
            "nightly_paid__1_to_2_years": (30, "ok"),
            "nightly_paid__5_plus_years": (70, "ok"),
            "hostel__1_to_2_years": (1, "ok"),
            "hostel__5_plus_years": (3, "ok"),
        },
    )
    out = indicators.add_shares(df)
    assert (
        share(out, "ta_families_length_of_stay_share", "nightly_paid__5_plus_years")["value"] == 70
    )
    assert share(out, "ta_families_length_of_stay_share", "hostel__5_plus_years")["value"] == 75


def test_ethnicity_share_of_known_excludes_not_known():
    df = rows(
        "ta_households_by_ethnicity",
        {"asian": (40, "ok"), "white": (10, "ok"), "not_known": (50, "ok")},
    )
    out = indicators.add_shares(df)
    assert share(out, "ta_households_by_ethnicity_share", "asian")["value"] == 40
    assert share(out, "ta_households_by_ethnicity_share_of_known", "asian")["value"] == 80
    assert out[
        (out.indicator == "ta_households_by_ethnicity_share_of_known")
        & (out.breakdown == "not_known")
    ].empty


def test_out_of_area_share():
    df = pd.concat(
        [
            rows("ta_households_out_of_area", {"all": (25, "ok")}),
            rows("ta_households", {"all": (100, "ok")}),
        ],
        ignore_index=True,
    )
    out = indicators.add_ratios(df)
    assert share(out, "ta_households_out_of_area_share", "all")["value"] == 25
    validate(out)


def test_every_loader_indicator_is_in_the_dictionary():
    produced = {spec[1] for specs in mhclg_ta.SPECS.values() for spec in specs}
    produced |= {"housing_register_households", "social_lettings_total", "social_lettings_by_type"}
    produced |= {ind for _, ind, _ in lettings._1E_SPECS}
    produced |= {"ta_households_out_of_area_share"}
    from ta_london.ingest import gla_council_homes, trust_for_london

    produced |= {ind for _, ind, _ in trust_for_london._T87_COLUMNS}
    produced |= {ind for _, ind, _ in trust_for_london._T88_COLUMNS}
    produced |= {"council_homes_started_gla", "council_homes_completed_gla"}
    assert gla_council_homes.SHEET
    produced |= {f"{i}_share" for i in indicators.SHARE_INDICATORS}
    produced |= {f"{i}_share_of_known" for i in indicators.SHARE_OF_KNOWN}
    assert produced <= set(indicators.load_dictionary())


def test_dictionary_entries_are_complete():
    for name, entry in indicators.load_dictionary().items():
        for field in ("label", "definition", "unit", "source_id", "caveats"):
            assert entry.get(field), (name, field)

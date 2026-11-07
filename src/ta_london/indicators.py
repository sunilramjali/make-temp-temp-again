"""Derived indicators and the indicator dictionary.

Shares are calculated here, never in the app. A share is a breakdown value divided by the sum of
its group (the breakdowns of one indicator for one area and period, which partition a total).
If any part of a group is suppressed or missing the share is NaN, never a partial calculation.
"""

import numpy as np
import pandas as pd
import yaml

from ta_london.paths import ROOT

DICTIONARY_PATH = ROOT / "src" / "ta_london" / "indicators.yaml"

# Indicators whose breakdowns partition a total. Length-of-stay shares are within each
# accommodation type (the part of the breakdown before '__').
SHARE_INDICATORS = [
    "ta_households_by_accommodation_type",
    "ta_households_by_composition",
    "ta_households_by_duty",
    "ta_households_by_age_of_main_applicant",
    "ta_households_by_ethnicity",
    "ta_households_by_ethnicity_detail",
    "ta_families_by_accommodation_type",
    "ta_families_length_of_stay",
    "ta_children_by_age",
    "ta_out_of_area_by_accommodation_type",
    "ta_out_of_area_by_composition",
    "relief_end_decisions",
    "main_duty_ended_by_reason",
    "main_duty_owed_by_priority_need",
    "ta_households_by_accommodation_type_avg4q",
]
# Also reported as a share of households whose ethnicity is known.
SHARE_OF_KNOWN = ["ta_households_by_ethnicity", "ta_households_by_ethnicity_detail"]
_KEYS = ["area_code", "area_name", "period", "period_type", "period_end", "source_id"]


def _shares(sub: pd.DataFrame, indicator: str, name: str) -> pd.DataFrame:
    sub = sub.copy()
    part = (
        sub["breakdown"].str.split("__").str[0]
        if indicator == "ta_families_length_of_stay"
        else "all"
    )
    sub["_group"] = part
    keys = [*_KEYS, "_group"]
    grouped = sub.groupby(keys)["value"]
    total = grouped.transform("sum")
    any_nan = grouped.transform(lambda s: s.isna().any())
    any_suppressed = (
        sub.assign(_s=sub["value_status"].eq("suppressed")).groupby(keys)["_s"].transform("any")
    )
    ok = ~any_nan & (total > 0)
    out = sub.drop(columns=["_group"])
    out["indicator"] = name
    out["value"] = np.where(ok, 100 * sub["value"] / total.where(total > 0), np.nan)
    out["value_status"] = np.where(ok, "ok", np.where(any_suppressed, "suppressed", "missing"))
    out["unit"] = "percent"
    return out


def add_shares(df: pd.DataFrame) -> pd.DataFrame:
    """Append share indicators (percent) for the partitioned indicators."""
    extra = []
    for indicator in SHARE_INDICATORS:
        sub = df[df["indicator"] == indicator]
        if sub.empty:
            continue
        extra.append(_shares(sub, indicator, f"{indicator}_share"))
        if indicator in SHARE_OF_KNOWN:
            known = sub[sub["breakdown"] != "not_known"]
            extra.append(_shares(known, indicator, f"{indicator}_share_of_known"))
    out = pd.concat([df, *extra], ignore_index=True)
    return out.sort_values(["area_code", "indicator", "breakdown", "period_end"]).reset_index(
        drop=True
    )


# (new indicator, numerator, denominator, multiplier). Same area and period; breakdown 'all'.
# households_in_area is in thousands, so households / (thousands * 1000) * 100 = 0.1 * ratio.
RATIOS = [
    ("ta_households_out_of_area_share", "ta_households_out_of_area", "ta_households", 100.0),
    ("ta_households_pct_of_households", "ta_households", "households_in_area", 0.1),
    (
        "ta_households_with_children_pct_of_households",
        "ta_households_with_children",
        "households_in_area",
        0.1,
    ),
]


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Append ratio indicators (percent) built from two stored indicators."""
    keys = [*_KEYS]
    extra = []
    for name, numerator, denominator, multiplier in RATIOS:
        num = df[(df["indicator"] == numerator) & (df["breakdown"] == "all")]
        den = df[(df["indicator"] == denominator) & (df["breakdown"] == "all")]
        if num.empty or den.empty:
            continue
        m = num.merge(den[[*keys, "value", "value_status"]], on=keys, suffixes=("", "_den"))
        ok = m["value"].notna() & m["value_den"].notna() & (m["value_den"] > 0)
        suppressed = m["value_status"].eq("suppressed") | m["value_status_den"].eq("suppressed")
        out = m[[*keys, "breakdown"]].copy()
        out["indicator"] = name
        out["value"] = np.where(
            ok, multiplier * m["value"] / m["value_den"].where(m["value_den"] > 0), np.nan
        )
        out["value_status"] = np.where(ok, "ok", np.where(suppressed, "suppressed", "missing"))
        out["unit"] = "percent"
        extra.append(out[df.columns])
    return pd.concat([df, *extra], ignore_index=True)


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Two simple derived values the app shows, kept here so the app does no maths:
    the weekly market-minus-social rent gap, and children under 5 (sum of TA8 ages 0-4)."""
    keys = [*_KEYS]
    extra = []
    market = df[df["indicator"] == "market_rent_weekly"]
    social = df[df["indicator"] == "social_relet_rent_weekly"]
    if not market.empty and not social.empty:
        m = market.merge(social[[*keys, "value"]], on=keys, suffixes=("", "_social"))
        ok = m["value"].notna() & m["value_social"].notna()
        out = m[[*keys, "breakdown"]].copy()
        out["indicator"] = "rent_gap_weekly"
        out["value"] = np.where(ok, m["value"] - m["value_social"], np.nan)
        out["value_status"] = np.where(ok, "ok", "missing")
        out["unit"] = "gbp_per_week"
        extra.append(out[df.columns])
    ages = df[
        (df["indicator"] == "ta_children_by_age")
        & df["breakdown"].isin([f"age_{a}" for a in range(5)])
    ]
    if not ages.empty:
        g = ages.groupby(keys)["value"]
        out = g.sum(min_count=5).reset_index()  # NaN unless all five ages are present
        out["breakdown"] = "all"
        out["indicator"] = "ta_children_under_5"
        out["value_status"] = np.where(out["value"].notna(), "ok", "missing")
        out["unit"] = "children"
        out["value"] = out["value"].astype(float)
        extra.append(out[df.columns])
    return pd.concat([df, *extra], ignore_index=True)


def load_dictionary(path=DICTIONARY_PATH) -> dict[str, dict]:
    """Indicator dictionary keyed by name, with entries for the derived share indicators."""
    entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = {e["name"]: e for e in entries}
    for base in SHARE_INDICATORS:
        if base not in out:
            continue
        b = out[base]
        out[f"{base}_share"] = {
            **b,
            "name": f"{base}_share",
            "label": f"{b['label']} (share, %)",
            "definition": f"Each breakdown as a percentage of its group total. {b['definition']}",
            "unit": "percent",
        }
        if base in SHARE_OF_KNOWN:
            out[f"{base}_share_of_known"] = {
                **out[f"{base}_share"],
                "name": f"{base}_share_of_known",
                "label": f"{b['label']} (share of known, %)",
                "caveats": f"Excludes households whose ethnicity is not known. {b['caveats']}",
            }
    return out


def assert_in_dictionary(df: pd.DataFrame, path=DICTIONARY_PATH) -> None:
    missing = sorted(set(df["indicator"]) - set(load_dictionary(path)))
    if missing:
        raise ValueError(f"Indicators missing from indicators.yaml: {missing}")

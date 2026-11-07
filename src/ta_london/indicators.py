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


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Append ratio indicators built from two stored indicators (same area and period)."""
    keys = [*_KEYS]
    num = df[(df["indicator"] == "ta_households_out_of_area") & (df["breakdown"] == "all")]
    den = df[(df["indicator"] == "ta_households") & (df["breakdown"] == "all")]
    if num.empty or den.empty:
        return df
    m = num.merge(den[[*keys, "value", "value_status"]], on=keys, suffixes=("", "_den"))
    ok = m["value"].notna() & m["value_den"].notna() & (m["value_den"] > 0)
    out = m[[*keys, "breakdown"]].copy()
    out["indicator"] = "ta_households_out_of_area_share"
    out["value"] = np.where(ok, 100 * m["value"] / m["value_den"].where(m["value_den"] > 0), np.nan)
    out["value_status"] = np.where(ok, "ok", "missing")
    out["unit"] = "percent"
    out = out[df.columns]
    return pd.concat([df, out], ignore_index=True)


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

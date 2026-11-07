"""Load and validate policy/services_map.csv.

What a borough *offers* is kept separate from evidence of *uptake* or *outcomes*. A row can have
an offer with no uptake or outcome evidence; the three states are derived, never assumed.

`service_category` must be one of SERVICE_CATEGORIES (the README's step 3 list) unless another
list is passed.
"""

import pandas as pd

from ta_london.paths import POLICY, SERVICES_MAP

# Categories from the README, Methodology step 3 ("prevention, PRS access, landlord incentives,
# deposits, allocations, tenancy support"). Add to this list only by team agreement.
SERVICE_CATEGORIES = [
    "prevention",
    "prs_access",
    "landlord_incentives",
    "deposits",
    "allocations",
    "tenancy_support",
]

REQUIRED_COLUMNS = [
    "borough",
    "service_category",
    "service_name",
    "description",
    "eligibility",
    "offered_source",
    "offered_date",
    "uptake_evidence",
    "outcome_evidence",
    "evidence_source",
    "families_or_pregnant_specific",
    "notes",
]


def load_services(path=SERVICES_MAP, allowed_categories=tuple(SERVICE_CATEGORIES)) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    if allowed_categories is not None:
        bad = sorted(set(df["service_category"]) - set(allowed_categories))
        if bad:
            raise ValueError(f"Unknown service_category values: {bad}")
    return df[REQUIRED_COLUMNS]


def add_evidence_states(df: pd.DataFrame) -> pd.DataFrame:
    """Add boolean columns saying what is recorded: offered / uptake / outcome."""
    out = df.copy()
    out["offered"] = out["offered_source"].str.strip() != ""
    out["has_uptake_evidence"] = out["uptake_evidence"].str.strip() != ""
    out["has_outcome_evidence"] = out["outcome_evidence"].str.strip() != ""
    return out


def list_policy_documents(root=None) -> pd.DataFrame:
    """Markdown policy documents under policy/, with the folder they sit in.

    README files are skipped. `group` is the first folder under policy/ (national, newham,
    comparators) and `borough` the sub-folder for comparators, else blank.
    """
    root = POLICY if root is None else root
    rows = []
    for p in sorted(root.rglob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        rel = p.relative_to(root)
        parts = rel.parts
        rows.append(
            {
                "path": p,
                "relative_path": rel.as_posix(),
                "group": parts[0] if len(parts) > 1 else "",
                "borough": parts[1] if parts[0] == "comparators" and len(parts) > 2 else "",
                "name": p.stem,
            }
        )
    return pd.DataFrame(rows, columns=["path", "relative_path", "group", "borough", "name"])

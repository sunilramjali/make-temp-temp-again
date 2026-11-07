"""Shared display helpers for the Streamlit app. Display only: no cleaning or indicator maths.

Every number shown here is read from data/processed/indicators.parquet, which the pipeline builds.
Shares and ratios are calculated in src/ta_london/indicators.py, not here.
"""

import os
import threading

import pandas as pd
import plotly.express as px
import streamlit as st

from ta_london import pipeline
from ta_london.geography import ENGLAND_CODE, LONDON_CODE, NEWHAM_CODE
from ta_london.indicators import load_dictionary
from ta_london.paths import PROCESSED, ROOT, SOURCES_CSV
from ta_london.sources import load_sources

INDICATORS_PARQUET = PROCESSED / "indicators.parquet"
BRIEF = ROOT / "docs" / "newham_evidence_brief.md"
SOURCE_LINKS = ROOT / "docs" / "source_links.md"

NO_DATA_MESSAGE = (
    "No data loaded yet. Run `uv run python -m ta_london.pipeline` to build "
    "`data/processed/indicators.parquet` from the files in `data/raw/`."
)
# Set to "1" to stop the app building the data itself (used by tests).
NO_AUTOBUILD_ENV = "TA_LONDON_NO_AUTOBUILD"
_BUILD_LOCK = threading.Lock()
DESCRIPTIVE = "Descriptive, not causal: patterns shown here do not prove cause."

# Fixed colours so an area looks the same on every chart.
AREA_COLOURS = {
    "Newham": "#d62728",
    "London": "#1f77b4",
    "England": "#7f7f7f",
}
_EXTRA = ["#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf", "#bcbd22"]


def build_data_if_missing() -> str | None:
    """Run the pipeline once if the processed table is missing. Returns an error message or None.

    The processed table is generated, not committed, so a fresh clone has none. The raw files are
    in git, so the app can build it on first load instead of showing empty pages. The pipeline
    (all the cleaning logic) lives in src/; the app only triggers it.
    """
    if INDICATORS_PARQUET.exists():
        return None
    if os.environ.get(NO_AUTOBUILD_ENV) == "1":
        return NO_DATA_MESSAGE
    with _BUILD_LOCK:  # one build even if several pages load at once
        if INDICATORS_PARQUET.exists():
            return None
        with st.spinner("Building the data from data/raw/ (first run only, about 2 minutes)..."):
            try:
                pipeline.run()
            except Exception as exc:  # show the reason instead of a blank page
                return f"Building the data failed: {exc}. {NO_DATA_MESSAGE}"
    return None


@st.cache_data(show_spinner=False)
def _read_table(path: str, modified: float) -> pd.DataFrame:
    # `modified` is part of the cache key, so a rebuilt file is re-read without a restart.
    return pd.read_parquet(path)


def load_data() -> pd.DataFrame | None:
    """The tidy indicators table (built on first use if missing), or None if unavailable."""
    if build_data_if_missing() is not None:
        return None
    return _read_table(str(INDICATORS_PARQUET), INDICATORS_PARQUET.stat().st_mtime)


@st.cache_data
def dictionary() -> dict:
    return load_dictionary()


@st.cache_data
def load_source_register() -> pd.DataFrame:
    if not SOURCES_CSV.exists():
        return pd.DataFrame()
    return load_sources()


@st.cache_data
def read_doc(path: str) -> str:
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def doc_section(path: str, heading_prefix: str) -> str:
    """One '## ' section of a markdown file, found by the start of its heading."""
    text = read_doc(path)
    for block in ("\n" + text).split("\n## ")[1:]:
        if block.startswith(heading_prefix):
            return "## " + block.strip()
    return ""


def need_data() -> pd.DataFrame | None:
    """The data, or None after showing why it isn't available."""
    error = build_data_if_missing()
    if error is not None:
        st.warning(error)
        return None
    df = load_data()
    if df is None or df.empty:
        st.warning(NO_DATA_MESSAGE)
        return None
    return df


def label(indicator: str) -> str:
    return dictionary().get(indicator, {}).get("label", indicator)


_LABELS = {
    "bnb": "B&B",
    "la_ha_stock": "Council or HA stock",
    "nightly_paid": "Nightly paid",
    "private_sector": "Private sector",
    "other_or_not_known": "Other or not known",
    "s193_main_duty": "Main duty (s193)",
    "s189b_emergency_accommodation": "Emergency (s189B)",
    "asian_other": "Asian: other",
    "white_british": "White British",
    "75_plus": "75 and over",
    "5_plus_years": "5+ years",
    "6_to_12_months": "6 to 12 months",
}


def pretty(breakdown: str) -> str:
    """Readable text for a breakdown slug. Parts joined by '__' are labelled separately."""
    parts = []
    for part in breakdown.split("__"):
        if part in _LABELS:
            parts.append(_LABELS[part])
        elif part.startswith("age_"):
            parts.append("Age " + part[4:])
        else:
            parts.append(part.replace("_", " ").capitalize())
    return ": ".join(parts)


def caveat(indicator: str, show_definition: bool = True) -> None:
    entry = dictionary().get(indicator)
    if not entry:
        return
    with st.expander("Definition and caveats", expanded=False):
        if show_definition:
            st.markdown(f"**Definition.** {entry['definition']}")
        st.markdown(f"**Caveats.** {entry['caveats']}")


def source_footnote(df: pd.DataFrame) -> None:
    ids = sorted(set(df["source_id"]))
    if not ids:
        return
    register = load_source_register()
    parts = []
    for sid in ids:
        match = register[register["source_id"] == sid] if not register.empty else register
        if match.empty:
            parts.append(f"`{sid}` (not in sources.csv)")
        else:
            r = match.iloc[0]
            parts.append(f"{r['title']} ({r['publisher']}; {r['reference_period']})")
    st.caption("Source: " + "; ".join(parts))


def latest_period(sub: pd.DataFrame) -> pd.DataFrame:
    if sub.empty:
        return sub
    return sub[sub["period_end"] == sub["period_end"].max()]


def borough_names(df: pd.DataFrame) -> list[str]:
    boroughs = df[df["area_code"].str.startswith("E09")]
    return sorted(boroughs["area_name"].unique())


def area_codes(df: pd.DataFrame, names: list[str]) -> list[str]:
    lookup = df.drop_duplicates("area_code").set_index("area_name")["area_code"]
    return [lookup[n] for n in names if n in lookup.index]


def colour_map(names) -> dict[str, str]:
    cmap, extra = {}, iter(_EXTRA * 3)
    for n in names:
        cmap[n] = AREA_COLOURS.get(n) or next(extra)
    return cmap


def ranked_bar(sub: pd.DataFrame, indicator: str) -> None:
    """Ranked bars for the 33 boroughs, Newham highlighted. London and England shown as text."""
    boroughs = sub[sub["area_code"].str.startswith("E09")]
    shown = boroughs.dropna(subset=["value"]).sort_values("value", ascending=False)
    hidden = boroughs[boroughs["value"].isna()]
    shown = shown.assign(
        highlight=shown["area_code"].eq(NEWHAM_CODE).map({True: "Newham", False: "Other boroughs"})
    )
    unit = shown["unit"].iloc[0] if len(shown) else ""
    fig = px.bar(
        shown,
        x="area_name",
        y="value",
        color="highlight",
        color_discrete_map={"Newham": AREA_COLOURS["Newham"], "Other boroughs": "#9aa7b4"},
        labels={"area_name": "", "value": unit.replace("_", " ")},
        title=label(indicator),
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-60)
    st.plotly_chart(fig, width="stretch")
    refs = sub[sub["area_code"].isin([LONDON_CODE, ENGLAND_CODE])].dropna(subset=["value"])
    if not refs.empty:
        st.caption(
            "Reference: " + "; ".join(f"{r.area_name} {r.value:,.1f}" for r in refs.itertuples())
        )
    if not hidden.empty:
        st.caption(
            "Not shown (suppressed or missing in the source): "
            + ", ".join(sorted(hidden["area_name"].unique()))
        )
    estimated = shown[shown["value_status"] == "estimated"]
    if not estimated.empty:
        st.caption(
            "Estimated by MHCLG (imputed): " + ", ".join(sorted(estimated["area_name"].unique()))
        )


def compare_breakdown(
    df: pd.DataFrame,
    indicator: str,
    area_names: list[str],
    order: list[str] | None = None,
    horizontal: bool = False,
) -> pd.DataFrame:
    """Grouped bars of one indicator's breakdowns for the chosen areas (latest period)."""
    sub = latest_period(df[(df["indicator"] == indicator) & df["area_name"].isin(area_names)])
    if sub.empty:
        st.info("No data for this selection.")
        return sub
    sub = sub.assign(category=sub["breakdown"].map(pretty))
    plotted = sub.dropna(subset=["value"])
    cats = [pretty(b) for b in order] if order else None
    fig = px.bar(
        plotted,
        x="value" if horizontal else "category",
        y="category" if horizontal else "value",
        color="area_name",
        barmode="group",
        orientation="h" if horizontal else "v",
        color_discrete_map=colour_map(area_names),
        category_orders={"category": cats} if cats else None,
        labels={
            "value": plotted["unit"].iloc[0].replace("_", " ") if len(plotted) else "",
            "category": "",
        },
        hover_data={"value_status": True},
    )
    fig.update_layout(legend_title_text="", xaxis_tickangle=0 if horizontal else -30)
    st.plotly_chart(fig, width="stretch")
    gaps = sub[sub["value"].isna()]
    if not gaps.empty:
        st.caption(
            "No value (suppressed or not applicable in the source): "
            + ", ".join(
                sorted({f"{r.area_name}: {pretty(r.breakdown)}" for r in gaps.itertuples()})
            )
        )
    return sub


def trend(df: pd.DataFrame, indicator: str, area_names: list[str], breakdown: str = "all") -> None:
    sub = df[
        (df["indicator"] == indicator)
        & (df["breakdown"] == breakdown)
        & df["area_name"].isin(area_names)
    ].sort_values("period_end")
    if sub.empty:
        st.info("No data for this selection.")
        return
    fig = px.line(
        sub,
        x="period_end",
        y="value",
        color="area_name",
        markers=True,
        color_discrete_map=colour_map(area_names),
        labels={"period_end": "", "value": sub["unit"].iloc[0].replace("_", " ")},
        title=label(indicator),
    )
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    estimated = sub[sub["value_status"] == "estimated"]
    if not estimated.empty:
        st.caption(
            "Estimated by MHCLG (imputed): "
            + ", ".join(f"{r.area_name} {r.period_end.year}" for r in estimated.itertuples())
        )
    gaps = sub[sub["value"].isna()]
    if not gaps.empty:
        st.caption(f"{len(gaps)} point(s) missing in the source, shown as gaps.")


def indicator_explorer(
    page_title: str,
    description: str,
    indicators: list[str],
) -> None:
    """Page body for the borough ranking page: pick an indicator and period."""
    st.title(page_title)
    st.write(description)
    st.caption(DESCRIPTIVE)
    df = need_data()
    if df is None:
        return
    available = [
        i for i in indicators if not df[(df["indicator"] == i) & (df["breakdown"] == "all")].empty
    ]
    indicator = st.selectbox("Indicator", available, format_func=label)
    sub = df[(df["indicator"] == indicator) & (df["breakdown"] == "all")]
    periods = sub.sort_values("period_end", ascending=False)["period"].unique().tolist()
    period = st.selectbox("Period", periods)
    sub = sub[sub["period"] == period]
    ranked_bar(sub, indicator)
    caveat(indicator)
    source_footnote(sub)
    with st.expander("Data table"):
        st.dataframe(
            sub[["area_name", "value", "value_status", "unit"]].sort_values(
                "value", ascending=False
            ),
            hide_index=True,
        )

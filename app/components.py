"""Shared display helpers for the Streamlit app. Display only: no cleaning or indicator maths."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ta_london.paths import PROCESSED, SOURCES_CSV
from ta_london.sources import load_sources

INDICATORS_PARQUET = PROCESSED / "indicators.parquet"
NEWHAM_CODE = "E09000025"

NO_DATA_MESSAGE = (
    "No data loaded yet. Put the original files in `data/raw/`, log them in `data/sources.csv`, "
    "and run `uv run python -m ta_london.pipeline`."
)


@st.cache_data
def load_data() -> pd.DataFrame | None:
    """The tidy indicators table, or None if the pipeline hasn't produced it yet."""
    if not INDICATORS_PARQUET.exists():
        return None
    return pd.read_parquet(INDICATORS_PARQUET)


@st.cache_data
def load_source_register() -> pd.DataFrame:
    if not SOURCES_CSV.exists():
        return pd.DataFrame()
    return load_sources()


def caveat_box(
    text: str = "Descriptive, not causal: patterns shown here do not prove cause.",
) -> None:
    st.info(text)


def source_footnote(source_ids) -> None:
    ids = sorted(set(source_ids))
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
            parts.append(f"{r['title']} ({r['publisher']}, {r['reference_period']})")
    st.caption("Source: " + "; ".join(parts))


def indicator_explorer(page_title: str, description: str) -> None:
    """Generic page body: pick an indicator and period, show a ranked bar chart.

    Used by the four data pages until indicator-specific views are agreed.
    """
    st.title(page_title)
    st.write(description)
    caveat_box()

    df = load_data()
    if df is None or df.empty:
        st.warning(NO_DATA_MESSAGE)
        return

    indicator = st.selectbox("Indicator", sorted(df["indicator"].unique()))
    sub = df[df["indicator"] == indicator]
    breakdown = st.selectbox("Breakdown", sorted(sub["breakdown"].unique()))
    sub = sub[sub["breakdown"] == breakdown]
    period = st.selectbox("Period", sorted(sub["period"].unique(), reverse=True))
    sub = sub[sub["period"] == period]

    shown = sub.dropna(subset=["value"]).sort_values("value", ascending=False)
    hidden = sub[sub["value"].isna()]
    shown = shown.assign(
        highlight=shown["area_code"].eq(NEWHAM_CODE).map({True: "Newham", False: "Other"})
    )
    fig = px.bar(
        shown,
        x="area_name",
        y="value",
        color="highlight",
        color_discrete_map={"Newham": "#d62728", "Other": "#7f8c9b"},
        labels={"area_name": "", "value": shown["unit"].iloc[0] if len(shown) else ""},
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")
    if not hidden.empty:
        st.caption(
            "Not shown (suppressed or missing): " + ", ".join(sorted(hidden["area_name"].unique()))
        )
    source_footnote(sub["source_id"])

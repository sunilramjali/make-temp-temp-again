"""Shared display helpers for the Streamlit app. Display only: no cleaning or indicator maths.

Every number shown here is read from data/processed/indicators.parquet, which the pipeline builds.
Shares and ratios are calculated in src/ta_london/indicators.py, not here.
"""

import json
import os
import threading

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import viz
from ta_london import pipeline
from ta_london.boundaries import BOUNDARIES_GEOJSON
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
DESCRIPTIVE = (
    "These figures describe what is happening. They don't show why: a difference between two "
    "boroughs does not mean one thing caused another."
)

# Plain-English meanings for words that appear across the site. Shown in the sidebar on every page.
GLOSSARY = {
    "Temporary accommodation (TA)": "A place the council finds for a homeless household to stay "
    "until a settled home is found. It can last months or years.",
    "Nightly-paid accommodation": "Flats or rooms rented by the council from private owners by "
    "the night. Usually self-contained, often expensive.",
    "B&B": "Bed and breakfast hotel, often with shared kitchens and bathrooms. By law, families "
    "with children should not stay more than six weeks.",
    "Placed out of area": "Housed outside the household's own borough.",
    "Main duty": "The council's legal duty to house a homeless household until it can offer a "
    "settled home. It ends when the household accepts (or refuses) a suitable offer, among "
    "other reasons.",
    "Priority need": "The legal reason a household qualifies for the main duty, such as having "
    "children or being pregnant.",
    "Housing register": "The council's waiting list for social housing.",
    "Social housing": "Homes let by councils and housing associations at below-market rents.",
    "New lettings / re-lets": "A social home let to a new tenant. Re-lets are existing homes that "
    "became free; new lettings also include newly built homes.",
    "Re-let rate": "Re-lets as a share of all social homes in the borough: how often a social "
    "home becomes free.",
    "Private rented offer": "An offer of a home from a private landlord, which ends the main duty "
    "if accepted.",
    "Per 1,000 households": "A rate that allows fair comparison between big and small boroughs.",
    "Yearly average": "The average of the four quarterly counts in a year (published by Trust for "
    "London). Slightly different from a single-day count.",
    "Hidden or not published": "The source doesn't publish some small numbers, so people can't be "
    "identified, or a council didn't send its data. These are shown as gaps, never as zero.",
    "MHCLG": "Ministry of Housing, Communities and Local Government, which publishes the national "
    "homelessness figures.",
    "GLA": "Greater London Authority (the Mayor of London's office).",
    "CORE": "The national record of new social housing lettings.",
}


def glossary() -> None:
    """Sidebar glossary of the terms used on the site, so no page needs to assume them."""
    with st.sidebar.expander("What do these words mean?"):
        for term, meaning in GLOSSARY.items():
            st.markdown(f"**{term}**: {meaning}")


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
        with st.spinner("Building the data from data/raw/ (first run only, about 30 seconds)..."):
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
    "bnb": "B&B hotel",
    "la_ha_stock": "Council or housing association home",
    "nightly_paid": "Nightly-paid, private",
    "private_sector": "Private rented, leased by council",
    "hostel": "Hostel",
    "other": "Other",
    "other_or_not_known": "Other or not known",
    "not_known": "Not known",
    "adult_only": "Adults only, no children",
    "one_adult_female_with_children": "Single mother with children",
    "one_adult_male_with_children": "Single father with children",
    "one_adult_other_sex_with_children": "Single parent (other) with children",
    "two_adults_with_children": "Couple with children",
    "three_plus_adults_with_children": "Three or more adults with children",
    "less_than_6_months": "Under 6 months",
    "1_to_2_years": "1 to 2 years",
    "2_to_5_years": "2 to 5 years",
    "16_to_17": "16 to 17",
    "18_to_24": "18 to 24",
    "25_to_34": "25 to 34",
    "35_to_44": "35 to 44",
    "45_to_54": "45 to 54",
    "55_to_64": "55 to 64",
    "65_to_74": "65 to 74",
    "s193_main_duty": "Main duty (council must house until a settled home)",
    "s189b_emergency_accommodation": "Emergency stay while the council helps (relief duty)",
    "dependent_children": "Has children",
    "pregnant": "Pregnant",
    "vulnerable": "Vulnerable (e.g. illness, disability, age)",
    "emergency": "Emergency (e.g. fire or flood)",
    "ceased_eligible": "No longer eligible",
    "asian_other": "Asian: other",
    "white_british": "White British",
    "75_plus": "75 and over",
    "5_plus_years": "5+ years",
    "6_to_12_months": "6 to 12 months",
    "prs_offer_accepted": "Private rented offer accepted",
    "prs_offer_refused": "Private rented offer refused",
    "social_offer_accepted": "Social housing offer accepted",
    "social_offer_refused": "Social housing offer refused",
    "refused_ta_withdrew_or_lost_contact": "Refused the temporary home, withdrew or lost contact",
    "intentionally_homeless_from_ta": "Judged to have made themselves homeless from it",
    "voluntarily_left_ta": "Left of their own accord",
    "no_accommodation_secured": "Duty owed, no accommodation secured",
    "children_other_priority_need": "Children, other priority need",
    "yorkshire_humber": "Yorkshire and the Humber",
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
    with st.expander("What this measures, and what to watch out for", expanded=False):
        if show_definition:
            st.markdown(f"**What it measures.** {entry['definition']}")
        st.markdown(f"**Watch out for.** {entry['caveats']}")
        if entry.get("source_detail"):
            st.caption(f"Source detail: {entry['source_detail']}")


def source_footnote(df: pd.DataFrame) -> None:
    ids = sorted(set(df["source_id"]))
    if not ids:
        return
    register = load_source_register()
    parts = []
    for sid in ids:
        match = register[register["source_id"] == sid] if not register.empty else register
        if match.empty:
            parts.append(f"{sid} (source details missing)")
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


def apply_style() -> None:
    """Shared CSS (stat tiles, type scale). Call once at the top of every page."""
    st.markdown(viz.CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    apply_style()
    glossary()
    st.title(title)
    st.markdown(
        f'<p style="font-size:1.02rem;opacity:0.8;margin:-0.3rem 0 0.4rem 0">{subtitle}</p>',
        unsafe_allow_html=True,
    )
    st.caption(DESCRIPTIVE)


def chart_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<p style="font-weight:600;font-size:1.05rem;margin:0.9rem 0 0 0">{title}</p>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f'<p style="font-size:0.88rem;opacity:0.72;margin:0 0 0.2rem 0">{subtitle}</p>',
            unsafe_allow_html=True,
        )


def fmt(value: float, unit: str) -> str:
    """Readable number for labels, tiles and tooltips."""
    if value is None or pd.isna(value):
        return "not available"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit in ("per_1000_households",):
        return f"{value:.1f}"
    if unit == "gbp_per_week":
        return f"£{value:,.0f}"
    if unit == "days":
        return f"{value:,.0f} days"
    if unit == "thousand_households":
        return f"{value:,.0f}k"
    return f"{value:,.0f}"


def unit_label(unit: str) -> str:
    return {
        "percent": "% (share)",
        "per_1000_households": "per 1,000 households",
        "gbp_per_week": "£ per week",
        "thousand_households": "thousand households",
    }.get(unit, unit.replace("_", " "))


STATUS_TEXT = {
    "ok": "",
    "estimated": "Estimated by MHCLG",
    "suppressed": "Not published (small number)",
    "missing": "No data",
    "incomplete": "Incomplete: council data missing",
}


def table_view(frame: pd.DataFrame, key: str | None = None) -> None:
    """Every chart has a table twin: the accessible way to read exact values."""
    with st.expander("See the exact numbers"):
        st.dataframe(frame, hide_index=True, width="stretch", key=key)


def _show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})


def ranked_bar(sub: pd.DataFrame, indicator: str) -> None:
    """33 boroughs as thin horizontal bars, largest at the top. Newham carries the accent,
    every other borough recedes; London and England are labelled reference lines when the
    unit is a rate or share (a count for London would dwarf every borough)."""
    boroughs = sub[sub["area_code"].str.startswith("E09")]
    shown = boroughs.dropna(subset=["value"]).sort_values("value")
    hidden = boroughs[boroughs["value"].isna()]
    if shown.empty:
        st.info("No borough values for this selection.")
        return
    unit = shown["unit"].iloc[0]
    is_newham = shown["area_code"].eq(NEWHAM_CODE)
    is_incomplete = shown["value_status"].eq("incomplete")
    colours = [viz.accent() if n else viz.tok("deemph") for n in is_newham]
    text = [fmt(v, unit) if n else "" for v, n in zip(shown["value"], is_newham, strict=True)]
    fig = go.Figure(
        go.Bar(
            x=shown["value"],
            y=shown["area_name"],
            orientation="h",
            # Incomplete returns: hatched, so an under-count doesn't read as a real low value.
            marker={
                "color": colours,
                "pattern": {
                    "shape": ["/" if i else "" for i in is_incomplete],
                    "fgcolor": viz.tok("muted"),
                    "bgcolor": viz.tok("surface"),
                    "solidity": 0.35,
                },
            },
            width=0.62,
            text=text,
            textposition="outside",
            textfont={"color": viz.tok("ink"), "size": 12},
            cliponaxis=False,
            customdata=[
                fmt(v, unit) + (" (incomplete: some data missing)" if i else "")
                for v, i in zip(shown["value"], is_incomplete, strict=True)
            ],
            hovertemplate="%{y}: %{customdata}<extra></extra>",
        )
    )
    if unit in ("percent", "per_1000_households", "gbp_per_week", "days"):
        refs = sub[sub["area_code"].isin([LONDON_CODE, ENGLAND_CODE])].dropna(subset=["value"])
        for r in refs.itertuples():
            fig.add_vline(x=r.value, line={"color": viz.tok("muted"), "width": 1}, layer="below")
            fig.add_annotation(
                x=r.value,
                y=1.0,
                yref="paper",
                yanchor="bottom",
                text=f"{r.area_name} {fmt(r.value, unit)}",
                showarrow=False,
                font={"size": 11, "color": viz.tok("ink2")},
            )
    viz.style(
        fig,
        height=max(360, 22 * len(shown) + 70),
        legend=False,
        horizontal=True,
        x_title=unit_label(unit),
    )
    fig.update_layout(margin={"t": 30})
    _show(fig)
    notes = []
    if unit not in ("percent", "per_1000_households", "gbp_per_week", "days"):
        refs = sub[sub["area_code"].isin([LONDON_CODE, ENGLAND_CODE])].dropna(subset=["value"])
        if not refs.empty:
            notes.append(
                "For scale, the totals are: "
                + "; ".join(f"{r.area_name} {fmt(r.value, unit)}" for r in refs.itertuples())
                + "."
            )
    if not hidden.empty:
        notes.append(
            "Left out because the source doesn't publish a figure: "
            + ", ".join(sorted(hidden["area_name"].unique()))
            + "."
        )
    estimated = shown[shown["value_status"] == "estimated"]
    if not estimated.empty:
        notes.append(
            "Estimated by MHCLG (the council didn't send full figures): "
            + ", ".join(sorted(estimated["area_name"].unique()))
            + "."
        )
    if is_incomplete.any():
        notes.append(
            "Striped bars: the council's data is incomplete, so the real figure is probably "
            "higher: " + ", ".join(sorted(shown.loc[is_incomplete, "area_name"].unique())) + "."
        )
    for n in notes:
        st.caption(n)
    rank = shown.sort_values("value", ascending=False).reset_index(drop=True)
    table_view(
        pd.DataFrame(
            {
                "Rank (1 = highest)": rank.index + 1,
                "Borough": rank["area_name"],
                "Value": [fmt(v, unit) for v in rank["value"]],
                "Note": rank["value_status"].map(STATUS_TEXT).fillna(""),
            }
        )
    )


# Only rates and shares are mapped: counts on a map make the biggest boroughs look worst.
MAP_UNITS = ("percent", "per_1000_households")
_UNRELIABLE = ("suppressed", "missing", "incomplete")
# Required with any map drawn from the ONS boundaries: the two statements ONS lists for digital
# boundaries at ons.gov.uk/methodology/geography/licences. Year = boundary vintage (May 2024).
BOUNDARY_CREDIT = (
    "Source: Office for National Statistics licensed under the Open Government Licence v.3.0. "
    "Contains OS data © Crown copyright and database right 2024."
)


@st.cache_data
def _boundaries(path: str, modified: float) -> dict:
    with open(path) as f:
        return json.load(f)


def borough_map(sub: pd.DataFrame, indicator: str) -> None:
    """Choropleth of the 33 boroughs for one rate indicator and period. Boroughs with no
    reliable value (suppressed, missing or incomplete returns) are grey, never shaded as low.
    Newham is outlined in the accent colour. Hidden if the boundary file isn't built."""
    if not BOUNDARIES_GEOJSON.exists():
        st.caption("The map isn't available yet (the borough boundary file hasn't been built).")
        return
    boroughs = sub[sub["area_code"].str.startswith("E09")]
    if boroughs.empty:
        return
    unit = boroughs["unit"].iloc[0]
    if unit not in MAP_UNITS:
        raise ValueError(f"borough_map shows rates only, not {unit!r} ({indicator})")
    geo = _boundaries(str(BOUNDARIES_GEOJSON), BOUNDARIES_GEOJSON.stat().st_mtime)
    names = dict(load_data()[["area_code", "area_name"]].drop_duplicates().values)
    all_codes = [f["properties"]["area_code"] for f in geo["features"]]
    reliable = boroughs[~boroughs["value_status"].isin(_UNRELIABLE) & boroughs["value"].notna()]
    grey = [c for c in all_codes if c not in set(reliable["area_code"])]
    status = dict(boroughs[["area_code", "value_status"]].values)
    values = dict(boroughs[["area_code", "value"]].values)
    reason = {
        "incomplete": "council data incomplete",
        "suppressed": "not published",
        "missing": "no data",
    }

    ramp = viz.tok("ordinal")
    line = {"color": viz.tok("surface"), "width": 0.8}
    common = {"geojson": geo, "featureidkey": "properties.area_code", "hoverinfo": "text"}
    fig = go.Figure()
    fig.add_trace(
        go.Choropleth(
            **common,
            locations=reliable["area_code"],
            z=reliable["value"],
            colorscale=[[0, ramp[0]], [0.5, ramp[1]], [1, ramp[2]]],
            marker={"line": line},
            text=[f"{r.area_name}: {fmt(r.value, unit)}" for r in reliable.itertuples()],
            colorbar={
                "title": {"text": unit_label(unit), "side": "right"},
                "thickness": 10,
                "len": 0.7,
                "outlinewidth": 0,
                "tickfont": {"color": viz.tok("ink2"), "size": 11},
            },
        )
    )
    if grey:
        fig.add_trace(
            go.Choropleth(
                **common,
                locations=grey,
                z=[0] * len(grey),
                colorscale=[[0, viz.tok("neutral")], [1, viz.tok("neutral")]],
                showscale=False,
                marker={"line": line},
                text=[
                    f"{names.get(c, c)}: {fmt(values.get(c), unit)} "
                    f"(grey: {reason.get(status.get(c), 'no data')})"
                    for c in grey
                ],
            )
        )
    if NEWHAM_CODE in all_codes:
        fig.add_trace(
            go.Choropleth(
                **common,
                locations=[NEWHAM_CODE],
                z=[0],
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                showscale=False,
                marker={"line": {"color": viz.accent(), "width": 3}},
                text=[f"{names.get(NEWHAM_CODE, 'Newham')}: {fmt(values.get(NEWHAM_CODE), unit)}"],
            )
        )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        height=420,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": viz.FONT, "color": viz.tok("ink2")},
        dragmode=False,
    )
    _show(fig)
    st.caption(
        "Darker means higher. Newham has a blue outline. Grey boroughs have no reliable figure "
        "(not published, or the council's data is incomplete)"
        + (f": {', '.join(sorted(names.get(c, c) for c in grey))}." if grey else ".")
    )
    st.caption(BOUNDARY_CREDIT)


def compare_breakdown(
    df: pd.DataFrame,
    indicator: str,
    area_names: list[str],
    order: list[str] | None = None,
    horizontal: bool = True,
) -> pd.DataFrame:
    """Categories down the side, one thin bar per area (latest period). Only Newham's bars
    carry value labels; the rest are in the tooltip and the table."""
    sub = latest_period(df[(df["indicator"] == indicator) & df["area_name"].isin(area_names)])
    if sub.empty:
        st.info("No data for this selection.")
        return sub
    unit = sub["unit"].iloc[0]
    cats = order or list(dict.fromkeys(sub["breakdown"]))
    cats = [c for c in cats if c in set(sub["breakdown"])]
    present = [a for a in area_names if a in set(sub["area_name"])]
    colours = viz.area_colours(present)
    if len(cats) == 1:  # one value per area: a short list of thin bars, not one fat group
        a = sub.set_index("area_name").reindex(present)
        fig = go.Figure(
            go.Bar(
                y=present,
                x=a["value"],
                orientation="h",
                width=0.5,
                marker={"color": [colours[n] for n in present]},
                text=[fmt(v, unit) for v in a["value"]],
                textposition="outside",
                textfont={"color": viz.tok("ink"), "size": 12},
                cliponaxis=False,
                hovertemplate="%{y}: %{text}<extra></extra>",
            )
        )
        viz.style(
            fig,
            height=70 + 40 * len(present),
            legend=False,
            horizontal=True,
            x_title=unit_label(unit),
        )
        fig.update_layout(yaxis={"autorange": "reversed"})
        _show(fig)
        table_view(pd.DataFrame({"Area": present, "Value": [fmt(v, unit) for v in a["value"]]}))
        return sub
    fig = go.Figure()
    for area in present:
        a = sub[sub["area_name"] == area].set_index("breakdown").reindex(cats)
        values = a["value"].tolist()
        fig.add_trace(
            go.Bar(
                name=area,
                y=[pretty(c) for c in cats],
                x=values,
                orientation="h",
                marker={"color": colours[area]},
                text=[fmt(v, unit) if area == "Newham" else "" for v in values],
                textposition="outside",
                textfont={"color": viz.tok("ink"), "size": 11},
                cliponaxis=False,
                customdata=[fmt(v, unit) for v in values],
                hovertemplate=f"{area} · %{{y}}: %{{customdata}}<extra></extra>",
            )
        )
    n_bars = len(cats) * len(present)
    viz.style(
        fig,
        height=max(300, 16 * n_bars + 34 * len(cats) + 60),
        legend=len(present) > 1,
        horizontal=True,
        x_title=unit_label(unit),
    )
    fig.update_layout(
        barmode="group", yaxis={"autorange": "reversed"}, legend={"traceorder": "normal"}
    )
    _show(fig)
    gaps = sub[sub["value"].isna()]
    if not gaps.empty:
        st.caption(
            "No figure published for: "
            + ", ".join(
                sorted({f"{r.area_name}: {pretty(r.breakdown)}" for r in gaps.itertuples()})
            )
        )
    table = sub.pivot_table(index="breakdown", columns="area_name", values="value").reindex(cats)
    table = table[[a for a in present if a in table.columns]]
    table.index = [pretty(c) for c in table.index]
    table_view(table.map(lambda v: fmt(v, unit)).reset_index(names="Category"))
    return sub


def _end_label(fig: go.Figure, x, y, text: str) -> None:
    fig.add_annotation(
        x=x,
        y=y,
        text=text,
        showarrow=False,
        xanchor="left",
        xshift=8,
        font={"size": 11, "color": viz.tok("ink2")},
    )


def _line(fig: go.Figure, name: str, x, y, colour: str, unit: str) -> None:
    fig.add_trace(
        go.Scatter(
            name=name,
            x=x,
            y=y,
            mode="lines+markers",
            line={"color": colour, "width": 2, "shape": "linear"},
            marker={"size": 8, "color": colour, "line": {"color": viz.tok("surface"), "width": 2}},
            customdata=[fmt(v, unit) for v in y],
            hovertemplate=f"{name}<br>%{{x|%Y}}: %{{customdata}}<extra></extra>",
            connectgaps=False,
        )
    )


def _date_range(fig: go.Figure, dates: pd.Series) -> None:
    """Fix the x range to the data, plus room on the right for end labels."""
    lo, hi = dates.min(), dates.max()
    pad = (hi - lo) * 0.12
    fig.update_xaxes(range=[lo - (hi - lo) * 0.02, hi + pad])


def trend(df: pd.DataFrame, indicator: str, area_names: list[str], breakdown: str = "all") -> None:
    """One 2px line per area, value labelled at the end of each line (up to 4 lines)."""
    sub = df[
        (df["indicator"] == indicator)
        & (df["breakdown"] == breakdown)
        & df["area_name"].isin(area_names)
    ].sort_values("period_end")
    if sub.empty:
        st.info("No data for this selection.")
        return
    unit = sub["unit"].iloc[0]
    present = [a for a in area_names if a in set(sub["area_name"])]
    colours = viz.area_colours(present)
    fig = go.Figure()
    for area in present:
        a = sub[sub["area_name"] == area]
        _line(fig, area, a["period_end"], a["value"].tolist(), colours[area], unit)
    if len(present) <= 4:
        ends = sub.dropna(subset=["value"]).sort_values("period_end").groupby("area_name").tail(1)
        span = (sub["value"].max() - min(0, sub["value"].min())) or 1
        for r in ends.itertuples():
            others = ends[ends["area_name"] != r.area_name]["value"]
            # skip a label that would sit within 6% of the axis height of another end-label
            if (abs(others - r.value) < 0.06 * span).any() and r.area_name != "Newham":
                continue
            _end_label(fig, r.period_end, r.value, fmt(r.value, unit))
    add_series_break(fig, indicator)
    viz.style(fig, height=360, legend=len(present) > 1, y_title=unit_label(unit))
    _date_range(fig, sub["period_end"])
    fig.update_layout(hovermode="x unified" if len(present) > 1 else "closest")
    fig.update_xaxes(
        showspikes=True, spikecolor=viz.tok("axis"), spikethickness=1, spikedash="solid"
    )
    _show(fig)
    estimated = sub[sub["value_status"] == "estimated"]
    if not estimated.empty:
        st.caption(
            "Estimated by MHCLG: "
            + ", ".join(f"{r.area_name} {r.period_end.year}" for r in estimated.itertuples())
        )
    gaps = sub[sub["value"].isna()]
    if not gaps.empty:
        st.caption(f"{len(gaps)} year(s) have no published figure; these show as gaps in the line.")
    table = sub.pivot_table(index="period", columns="area_name", values="value")
    table = table[[a for a in present if a in table.columns]]
    table_view(table.map(lambda v: fmt(v, unit)).reset_index(names="Period"))


def add_series_break(fig: go.Figure, indicator: str) -> None:
    """Solid hairline where the source says the series definitions changed (indicators.yaml)."""
    when = dictionary().get(indicator, {}).get("series_break_date")
    if not when:
        return
    fig.add_vline(x=when, line={"color": viz.tok("muted"), "width": 1})
    fig.add_annotation(
        x=when,
        y=1,
        yref="paper",
        yanchor="bottom",
        text="Counting method changed",
        showarrow=False,
        font={"size": 11, "color": viz.tok("muted")},
    )


def stacked_trend(df: pd.DataFrame, indicator: str, area_name: str, order=None) -> None:
    """One line per breakdown for one area. Lines, not stacked areas: each type's own path is
    readable, which a stack of six translucent bands is not."""
    sub = df[(df["indicator"] == indicator) & (df["area_name"] == area_name)].sort_values(
        "period_end"
    )
    if sub.empty:
        st.info("No data for this selection.")
        return
    unit = sub["unit"].iloc[0]
    keys = [
        k for k in (order or list(dict.fromkeys(sub["breakdown"]))) if k in set(sub["breakdown"])
    ]
    colours = viz.series_colours(keys)
    fig = go.Figure()
    for k in keys:
        a = sub[sub["breakdown"] == k]
        _line(fig, pretty(k), a["period_end"], a["value"].tolist(), colours[k], unit)
    # label only the largest series at the end; legend and tooltip carry the rest
    latest = sub[sub["period_end"] == sub["period_end"].max()].dropna(subset=["value"])
    if not latest.empty:
        top = latest.sort_values("value").iloc[-1]
        _end_label(
            fig, top.period_end, top.value, f"{pretty(top.breakdown)} {fmt(top.value, unit)}"
        )
    add_series_break(fig, indicator)
    viz.style(fig, height=380, legend=True, y_title=unit_label(unit))
    _date_range(fig, sub["period_end"])
    fig.update_layout(hovermode="x unified", margin={"r": 150})
    _show(fig)
    if dictionary().get(indicator, {}).get("series_break"):
        st.caption(
            "Counting method changed, so compare before and after with care: "
            + dictionary()[indicator]["series_break"]
        )
    table = sub.pivot_table(index="period", columns="breakdown", values="value")[keys]
    table.columns = [pretty(c) for c in table.columns]
    table_view(table.map(lambda v: fmt(v, unit)).reset_index(names="Year"))


def friendly_period(period: str, period_type: str, period_end) -> str:
    """The source's period written out in words, e.g. '2026-Q1' -> '31 March 2026'."""
    end = pd.Timestamp(period_end)
    if period_type in ("quarter_end", "snapshot"):
        return f"{end.day} {end:%B %Y}"
    if period_type == "quarter":
        start = end - pd.offsets.QuarterBegin(startingMonth=1)
        return f"{start:%B} to {end:%B %Y}"
    if period_type == "financial_year":
        return f"April {end.year - 1} to March {end.year}"
    if period_type == "calendar_year_average":
        return f"{period} (yearly average)"
    return period


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def indicator_explorer(
    page_title: str,
    description: str,
    indicators: list[str],
) -> None:
    """Page body for the borough ranking page: pick an indicator and period."""
    page_header(page_title, description)
    df = need_data()
    if df is None:
        return
    available = [
        i for i in indicators if not df[(df["indicator"] == i) & (df["breakdown"] == "all")].empty
    ]
    c1, c2 = st.columns([3, 1])
    indicator = c1.selectbox("What do you want to compare?", available, format_func=label)
    sub = df[(df["indicator"] == indicator) & (df["breakdown"] == "all")]
    periods = sub.sort_values("period_end", ascending=False).drop_duplicates("period")
    words = {
        r.period: friendly_period(r.period, r.period_type, r.period_end)
        for r in periods.itertuples()
    }
    period = c2.selectbox("When", list(words), format_func=words.get)
    sub = sub[sub["period"] == period]
    newham = sub[sub["area_code"] == NEWHAM_CODE]
    rank_note = ""
    boroughs = sub[sub["area_code"].str.startswith("E09")].dropna(subset=["value"])
    if not newham.empty and not boroughs.empty and pd.notna(newham["value"].iloc[0]):
        rank = int((boroughs["value"] > newham["value"].iloc[0]).sum()) + 1
        place = "the highest" if rank == 1 else f"{_ordinal(rank)} highest"
        rank_note = f"Newham is {place} of {len(boroughs)} boroughs. "
    chart_title(label(indicator), f"{rank_note}{words[period]}. Newham is shown in blue.")
    if not sub.empty and sub["unit"].iloc[0] in MAP_UNITS:
        left, right = st.columns(2)
        with left:
            borough_map(sub, indicator)
        with right:
            ranked_bar(sub, indicator)
    else:
        ranked_bar(sub, indicator)
        st.caption(
            "No map for counts: big boroughs would always look worst. Pick a share or a "
            "'per 1,000 households' measure to see a map."
        )
    caveat(indicator)
    source_footnote(sub)

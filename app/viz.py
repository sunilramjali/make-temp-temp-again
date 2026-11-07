"""Visual design tokens and figure styling for the dashboard. Display only.

Colours follow the dataviz reference palette, validated with its script (light and dark):
- categorical slots in fixed order; worst adjacent CVD delta E 9.1 light / 8.4 dark;
- Newham, London, England take slots 1-3 (validated all-pairs);
- the services matrix uses a 3-step single-hue ordinal ramp.
Light slots 3-5 are below 3:1 contrast on the light surface, so every chart ships with a
legend or direct labels plus a data-table view.
"""

import plotly.graph_objects as go
import streamlit as st

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

TOKENS = {
    "light": {
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "deemph": "#c9c7bf",  # 'other boroughs' bars: recede, still visible
        "surface": "#fcfcfb",
        "neutral": "#f0efec",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"],
        "ordinal": ["#86b6ef", "#3987e5", "#184f95"],
    },
    "dark": {
        "ink": "#f0efec",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "deemph": "#4a4a46",
        "surface": "#1a1a19",
        "neutral": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"],
        "ordinal": ["#86b6ef", "#3987e5", "#184f95"],
    },
}

FIXED_AREAS = ["Newham", "London", "England"]  # slots 1-3, the same on every chart
MAX_EXTRA_AREAS = 3  # slots 4-6; more would need a 7th+ hue (folded instead)


def mode() -> str:
    """Chart colour mode. Follows the page: if the app pins a theme base (.streamlit/config.toml),
    use it; otherwise follow the viewer's theme. Charts must never be dark on a light page."""
    try:
        base = st.get_option("theme.base")
        if base in ("light", "dark"):
            return base
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def tok(name: str):
    return TOKENS[mode()][name]


def accent() -> str:
    return tok("series")[0]


def area_colours(names) -> dict[str, str]:
    """Colour follows the area: Newham, London, England fixed; other areas take slots 4-6 in
    the order given (callers cap extra areas at MAX_EXTRA_AREAS)."""
    series = tok("series")
    out = {n: series[i] for i, n in enumerate(FIXED_AREAS)}
    extra = [n for n in names if n not in out]
    for i, n in enumerate(extra[:MAX_EXTRA_AREAS]):
        out[n] = series[3 + i]
    return out


def series_colours(keys) -> dict[str, str]:
    """Fixed-order categorical slots for non-area series (e.g. accommodation types)."""
    series = tok("series")
    return {k: series[i % len(series)] for i, k in enumerate(keys)}


def style(
    fig: go.Figure,
    *,
    height: int = 380,
    legend: bool = True,
    horizontal: bool = False,
    x_title: str = "",
    y_title: str = "",
) -> go.Figure:
    """Apply the shared look: transparent background (sits on the page in both modes),
    hairline solid grid on the value axis only, muted axis text, legend top-left."""
    value_axis = "xaxis" if horizontal else "yaxis"
    cat_axis = "yaxis" if horizontal else "xaxis"
    fig.update_layout(
        height=height,
        font={"family": FONT, "size": 13, "color": tok("ink2")},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 24, "t": 36 if legend else 12, "b": 8},
        showlegend=legend,
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.02,
            "yanchor": "bottom",
            "title": {"text": ""},
            "font": {"color": tok("ink2"), "size": 12},
            "bgcolor": "rgba(0,0,0,0)",
        },
        hoverlabel={
            "bgcolor": tok("surface"),
            "bordercolor": tok("grid"),
            "font": {"family": FONT, "color": tok("ink"), "size": 12},
        },
        bargap=0.35,
        bargroupgap=0.12,
        barcornerradius=4,
        title=None,
    )
    fig.update_layout(
        {
            value_axis: {
                "showgrid": True,
                "gridcolor": tok("grid"),
                "gridwidth": 1,
                "zeroline": False,
                "showline": False,
                "tickfont": {"color": tok("muted"), "size": 12},
                "title": {"text": x_title if horizontal else y_title, "font": {"size": 12}},
                "separatethousands": True,
                "automargin": True,
            },
            cat_axis: {
                "showgrid": False,
                "zeroline": False,
                "showline": True,
                "linecolor": tok("axis"),
                "linewidth": 1,
                "ticks": "",
                "tickfont": {"color": tok("ink2"), "size": 12},
                "title": {"text": y_title if horizontal else x_title, "font": {"size": 12}},
                "automargin": True,
            },
        }
    )
    return fig


CSS = """
<style>
  /* Stat tiles: quiet card, proportional figures, sentence-case label. */
  div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.22);
    border-radius: 10px;
    padding: 14px 16px 12px 16px;
  }
  div[data-testid="stMetricValue"] { font-weight: 600; font-variant-numeric: normal; }
  div[data-testid="stMetricLabel"] p { font-size: 0.85rem; opacity: 0.85; }
  /* Page rhythm */
  .block-container { padding-top: 2.2rem; max-width: 1180px; }
  h1 { font-weight: 650; letter-spacing: -0.01em; }
  h2, h3 { font-weight: 600; }
  [data-testid="stMarkdownContainer"] p.page-sub {
    font-size: 1.02rem; opacity: 0.8; margin-top: -0.4rem; margin-bottom: 0.6rem; }
  [data-testid="stMarkdownContainer"] p.chart-title {
    font-weight: 600; font-size: 1.05rem; margin: 0.9rem 0 0 0; }
  [data-testid="stMarkdownContainer"] p.chart-sub {
    font-size: 0.88rem; opacity: 0.72; margin: 0 0 0.2rem 0; }
  [data-testid="stMarkdownContainer"] p.hero {
    font-size: 3.6rem; font-weight: 650; line-height: 1.0; margin: 0.4rem 0 0.2rem 0; }
  [data-testid="stMarkdownContainer"] p.hero-label {
    font-size: 1.02rem; opacity: 0.8; margin-bottom: 1.1rem; max-width: 46rem; }
  .pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem;
          border: 1px solid rgba(128,128,128,0.35); margin-right: 6px; opacity: 0.85; }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
            margin-right: 6px; vertical-align: baseline; }
</style>
"""

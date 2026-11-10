import plotly.graph_objects as go
import streamlit as st

import viz
from components import (
    borough_map,
    borough_names,
    caveat,
    chart_title,
    compare_breakdown,
    doc_section,
    fmt,
    need_data,
    page_header,
    ranked_bar,
    source_footnote,
    table_view,
    trend,
)

st.set_page_config(page_title="Social housing · TA in London", layout="wide")
page_header(
    "Is social housing enough?",
    "The housing register (waiting list), new social lettings, new council homes, turnover and "
    "rents. The measures use different definitions and dates, so they show scale, "
    "not exact ratios.",
)

df = need_data()
if df is None:
    st.stop()

defaults = [n for n in ["Newham", "Brent", "Lambeth", "Tower Hamlets"] if n in borough_names(df)]
areas = st.multiselect(
    "Boroughs to show (up to four)",
    borough_names(df),
    default=defaults,
    max_selections=1 + viz.MAX_EXTRA_AREAS,
)
if not areas:
    st.info("Choose at least one borough.")
    st.stop()

st.warning(
    "**CORE lettings data for 2024/25 is incomplete.** Barnet, Camden, Greenwich and Wandsworth "
    "did not submit, so their lettings and churn figures are under-counts. The housing register "
    "is a different source (a council return) and does not have this gap."
)

tabs = st.tabs(
    [
        "Housing register",
        "New lettings",
        "New council homes (GLA)",
        "Churn and rents",
        "Barriers to entry",
    ]
)

with tabs[0]:
    chart_title(
        "Households on the housing register, 2012 to 2025",
        "Newham's register has grown every year since 2018 and is the largest in London.",
    )
    trend(df, "housing_register_households", areas)
    st.caption(
        "A register is not the same as households waiting for social housing: councils review "
        "registers at different times and some households are on several. Big jumps for a "
        "single borough often reflect a change in register practice."
    )
    reg = df[(df.indicator == "housing_register_households")]
    latest = reg[reg.period_end == reg.period_end.max()]
    chart_title("Housing register by borough, 31 March 2025", "")
    ranked_bar(latest, "housing_register_households")
    caveat("housing_register_households")
    source_footnote(reg)

with tabs[1]:
    chart_title(
        "New social lettings per year",
        "Newham made 711 new social lettings in 2024/25, down from 966 the year before.",
    )
    trend(df, "social_lettings_total", areas)
    lets = df[(df.indicator == "social_lettings_total")]
    latest = lets[lets.period_end == lets.period_end.max()]
    chart_title("New social lettings by borough, 2024/25", "Four boroughs did not submit data.")
    ranked_bar(latest, "social_lettings_total")
    chart_title("Lettings by tenure and landlord, 2024/25", "")
    compare_breakdown(df, "social_lettings_by_type", areas)
    caveat("social_lettings_total")
    source_footnote(lets)

with tabs[2]:
    st.write(
        "Council homes started and completed through GLA programmes. Other council homes are in "
        "MHCLG statistics, so this is part of new supply, not all of it."
    )
    chart_title("Council homes completed via GLA programmes", "Financial years from 2018-19.")
    trend(df, "council_homes_completed_gla", areas)
    chart_title("Council homes started via GLA programmes", "")
    trend(df, "council_homes_started_gla", areas)
    done = df[df.indicator == "council_homes_completed_gla"]
    chart_title("Completions by borough, 2025-26", "")
    ranked_bar(done[done.period_end == done.period_end.max()], "council_homes_completed_gla")
    caveat("council_homes_completed_gla")
    source_footnote(done)

with tabs[3]:
    churn = df[(df.indicator == "social_relet_rate") & (df.breakdown == "all")]
    chart_title(
        "Share of social homes re-let in 2024/25",
        "Newham re-let 1.4% of its social stock, the lowest of the boroughs that submitted data.",
    )
    left, right = st.columns(2)
    with left:
        borough_map(churn, "social_relet_rate")
    with right:
        ranked_bar(churn, "social_relet_rate")
    st.caption(
        "Barnet, Camden, Greenwich and Wandsworth did not submit CORE data, so their low rates "
        "are not reliable."
    )
    caveat("social_relet_rate")
    pct = df[(df.indicator == "social_rent_pct_of_market_rent") & (df.breakdown == "all")]
    chart_title(
        "Social re-let rent as a share of market rent, 2024/25",
        "Averages are not matched by property size.",
    )
    left, right = st.columns(2)
    with left:
        borough_map(pct, "social_rent_pct_of_market_rent")
    with right:
        ranked_bar(pct, "social_rent_pct_of_market_rent")
    caveat("social_rent_pct_of_market_rent")
    chart_title(
        "Average weekly rent: social re-let vs private market, 2024/25",
        "The gap is what a family leaving TA for private renting has to bridge.",
    )
    rents = df[
        df.indicator.isin(["social_relet_rent_weekly", "market_rent_weekly", "rent_gap_weekly"])
    ]
    rents = rents[rents.area_name.isin(areas)].dropna(subset=["value"])
    wide = rents.pivot_table(index="area_name", columns="indicator", values="value").dropna()
    if not wide.empty:
        wide = wide.sort_values("market_rent_weekly")
        social_c, market_c = viz.tok("series")[2], viz.tok("series")[1]
        fig = go.Figure()
        for name, row in wide.iterrows():
            fig.add_trace(
                go.Scatter(
                    x=[row.social_relet_rent_weekly, row.market_rent_weekly],
                    y=[name, name],
                    mode="lines",
                    line={"color": viz.tok("axis"), "width": 2},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig.add_annotation(
                x=row.market_rent_weekly,
                y=name,
                xanchor="left",
                xshift=10,
                showarrow=False,
                text=f"gap {fmt(row.rent_gap_weekly, 'gbp_per_week')}",
                font={"size": 11, "color": viz.tok("ink2")},
            )
        for col, label_, colour in [
            ("social_relet_rent_weekly", "Social re-let", social_c),
            ("market_rent_weekly", "Private market", market_c),
        ]:
            fig.add_trace(
                go.Scatter(
                    x=wide[col],
                    y=wide.index,
                    mode="markers",
                    name=label_,
                    marker={
                        "size": 11,
                        "color": colour,
                        "line": {"color": viz.tok("surface"), "width": 2},
                    },
                    customdata=[fmt(v, "gbp_per_week") for v in wide[col]],
                    hovertemplate=f"%{{y}} · {label_}: %{{customdata}} a week<extra></extra>",
                )
            )
        viz.style(fig, height=max(220, 56 * len(wide) + 90), horizontal=True, x_title="£ per week")
        fig.update_layout(margin={"r": 110})
        st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})
        table_view(
            wide.reset_index()
            .rename(
                columns={
                    "area_name": "Borough",
                    "social_relet_rent_weekly": "Social re-let (£/week)",
                    "market_rent_weekly": "Private market (£/week)",
                    "rent_gap_weekly": "Gap (£/week)",
                }
            )
            .round(2)
        )
    caveat("market_rent_weekly")
    source_footnote(churn)

with tabs[4]:
    section = doc_section("docs/newham_evidence_brief.md", "6.")
    if section:
        st.markdown(section)
    else:
        st.info("`docs/newham_evidence_brief.md` not found.")

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
    "Is there enough social housing?",
    "Waiting lists, homes let to new tenants, new council homes, how often homes become free, "
    "and rents. These figures come from different sources and dates. Use them to get a sense of "
    "scale, not to work out exact ratios.",
)

df = need_data()
if df is None:
    st.stop()

defaults = [n for n in ["Newham", "Brent", "Lambeth", "Tower Hamlets"] if n in borough_names(df)]
areas = st.multiselect(
    "Choose up to four boroughs",
    borough_names(df),
    default=defaults,
    max_selections=1 + viz.MAX_EXTRA_AREAS,
)
if not areas:
    st.info("Choose at least one borough.")
    st.stop()

st.warning(
    "**Some lettings figures for 2024/25 are incomplete.** Barnet, Camden, Greenwich and "
    "Wandsworth didn't send their data to the national lettings record (CORE), so their lettings "
    "figures are too low. Waiting-list figures come from a different source and aren't affected."
)

tabs = st.tabs(
    [
        "Waiting list",
        "Homes let to new tenants",
        "New council homes",
        "Homes becoming free, and rents",
        "Who can apply",
    ]
)

with tabs[0]:
    chart_title(
        "Households on the social housing waiting list, 2012 to 2025",
        "Newham's waiting list has grown every year since 2018 and is the largest in London.",
    )
    trend(df, "housing_register_households", areas)
    st.caption(
        "The waiting list isn't an exact count of households in need. Councils review their "
        "lists at different times, and some households are on more than one list. A sudden jump "
        "for one borough often means the council changed its rules, not that need changed."
    )
    reg = df[(df.indicator == "housing_register_households")]
    latest = reg[reg.period_end == reg.period_end.max()]
    chart_title("Waiting list by borough, 31 March 2025", "")
    ranked_bar(latest, "housing_register_households")
    caveat("housing_register_households")
    source_footnote(reg)

with tabs[1]:
    chart_title(
        "Social homes let to new tenants each year",
        "Newham let 711 social homes to new tenants in 2024/25, down from 966 the year before.",
    )
    trend(df, "social_lettings_total", areas)
    lets = df[(df.indicator == "social_lettings_total")]
    latest = lets[lets.period_end == lets.period_end.max()]
    chart_title(
        "Social homes let to new tenants, by borough, 2024/25", "Four boroughs didn't send data."
    )
    ranked_bar(latest, "social_lettings_total")
    chart_title("Lettings by type of tenancy and landlord, 2024/25", "")
    compare_breakdown(df, "social_lettings_by_type", areas)
    caveat("social_lettings_total")
    source_footnote(lets)

with tabs[2]:
    st.write(
        "Council homes started and finished with funding from the Mayor of London (GLA). Some "
        "council homes are built without this funding, so these figures show part of the new "
        "supply, not all of it."
    )
    chart_title(
        "Council homes finished with Mayor of London funding",
        "Each year runs April to March, from 2018-19.",
    )
    trend(df, "council_homes_completed_gla", areas)
    chart_title("Council homes started with Mayor of London funding", "")
    trend(df, "council_homes_started_gla", areas)
    done = df[df.indicator == "council_homes_completed_gla"]
    chart_title("Council homes finished, by borough, 2025-26", "")
    ranked_bar(done[done.period_end == done.period_end.max()], "council_homes_completed_gla")
    caveat("council_homes_completed_gla")
    source_footnote(done)

with tabs[3]:
    churn = df[(df.indicator == "social_relet_rate") & (df.breakdown == "all")]
    chart_title(
        "Share of social homes let to a new tenant in 2024/25",
        "Only 1.4% of Newham's social homes became free and were let again: the lowest of the "
        "boroughs that sent data.",
    )
    left, right = st.columns(2)
    with left:
        borough_map(churn, "social_relet_rate")
    with right:
        ranked_bar(churn, "social_relet_rate")
    st.caption(
        "Barnet, Camden, Greenwich and Wandsworth didn't send full data, so their low figures "
        "aren't reliable."
    )
    caveat("social_relet_rate")
    pct = df[(df.indicator == "social_rent_pct_of_market_rent") & (df.breakdown == "all")]
    chart_title(
        "Social rent as a share of private rent, 2024/25",
        "Lower means social housing is much cheaper than renting privately. Averages don't "
        "account for home size.",
    )
    left, right = st.columns(2)
    with left:
        borough_map(pct, "social_rent_pct_of_market_rent")
    with right:
        ranked_bar(pct, "social_rent_pct_of_market_rent")
    caveat("social_rent_pct_of_market_rent")
    chart_title(
        "Average weekly rent: social home compared with private rent, 2024/25",
        "The gap is the extra a family would pay each week renting privately instead of in a "
        "social home.",
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
                text=f"{fmt(row.rent_gap_weekly, 'gbp_per_week')} more",
                font={"size": 11, "color": viz.tok("ink2")},
            )
        for col, label_, colour in [
            ("social_relet_rent_weekly", "Social rent", social_c),
            ("market_rent_weekly", "Private rent", market_c),
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
                    "social_relet_rent_weekly": "Social rent (£ a week)",
                    "market_rent_weekly": "Private rent (£ a week)",
                    "rent_gap_weekly": "Difference (£ a week)",
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
        st.info("This summary isn't available yet.")

import streamlit as st

from components import (
    DESCRIPTIVE,
    borough_names,
    caveat,
    compare_breakdown,
    doc_section,
    need_data,
    ranked_bar,
    source_footnote,
    trend,
)

st.set_page_config(page_title="Social housing", layout="wide")
st.title("Is social housing enough?")
st.write(
    "The housing register (waiting list), new social lettings, and how much social housing "
    "turns over. The measures use different definitions and dates, so they show scale, "
    "not exact ratios."
)
st.caption(DESCRIPTIVE)

df = need_data()
if df is None:
    st.stop()

defaults = [n for n in ["Newham", "Brent", "Lambeth", "Tower Hamlets"] if n in borough_names(df)]
areas = st.multiselect("Boroughs to show", borough_names(df), default=defaults)
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
    trend(df, "housing_register_households", areas)
    st.caption(
        "A register is not the same as households waiting for social housing: councils review "
        "registers at different times and some households are on several. Big jumps for a "
        "single borough often reflect a change in register practice."
    )
    reg = df[(df.indicator == "housing_register_households")]
    latest = reg[reg.period_end == reg.period_end.max()]
    ranked_bar(latest, "housing_register_households")
    caveat("housing_register_households")
    source_footnote(reg)

with tabs[1]:
    trend(df, "social_lettings_total", areas)
    lets = df[(df.indicator == "social_lettings_total")]
    latest = lets[lets.period_end == lets.period_end.max()]
    ranked_bar(latest, "social_lettings_total")
    st.subheader("Lettings by tenure and landlord (latest year)")
    compare_breakdown(df, "social_lettings_by_type", areas)
    caveat("social_lettings_total")
    source_footnote(lets)

with tabs[2]:
    st.write(
        "Council homes started and completed through GLA programmes. Other council homes are in "
        "MHCLG statistics, so this is part of new supply, not all of it."
    )
    trend(df, "council_homes_completed_gla", areas)
    trend(df, "council_homes_started_gla", areas)
    done = df[df.indicator == "council_homes_completed_gla"]
    ranked_bar(done[done.period_end == done.period_end.max()], "council_homes_completed_gla")
    caveat("council_homes_completed_gla")
    source_footnote(done)

with tabs[3]:
    churn = df[(df.indicator == "social_relet_rate") & (df.breakdown == "all")]
    ranked_bar(churn, "social_relet_rate")
    st.caption(
        "Barnet, Camden, Greenwich and Wandsworth did not submit CORE data, so their low rates "
        "are not reliable."
    )
    caveat("social_relet_rate")
    st.subheader("Average weekly rent: social re-lets vs private market")
    rents = df[df.indicator.isin(["social_relet_rent_weekly", "market_rent_weekly"])]
    rents = rents[rents.area_name.isin(areas)].dropna(subset=["value"])
    if not rents.empty:
        import plotly.express as px

        fig = px.bar(
            rents.assign(
                kind=rents.indicator.map(
                    {
                        "social_relet_rent_weekly": "Social re-let",
                        "market_rent_weekly": "Private market",
                    }
                )
            ),
            x="area_name",
            y="value",
            color="kind",
            barmode="group",
            labels={"area_name": "", "value": "£ per week", "kind": ""},
            color_discrete_map={"Social re-let": "#2ca02c", "Private market": "#ff7f0e"},
        )
        st.plotly_chart(fig, width="stretch")
    caveat("market_rent_weekly")
    source_footnote(churn)

with tabs[4]:
    section = doc_section("docs/newham_evidence_brief.md", "6.")
    if section:
        st.markdown(section)
    else:
        st.info("`docs/newham_evidence_brief.md` not found.")

import plotly.graph_objects as go
import streamlit as st

import viz
from components import (
    borough_names,
    caveat,
    chart_title,
    compare_breakdown,
    fmt,
    latest_period,
    need_data,
    page_header,
    source_footnote,
    table_view,
)
from ta_london.geography import LONDON_CODE, NEWHAM_CODE

st.set_page_config(page_title="Demographics · TA in London", layout="wide")
page_header(
    "Who is in temporary accommodation?",
    "Household type, age, ethnicity and children in temporary accommodation (TA): Newham "
    "compared with London and England, at 31 March 2026.",
)

df = need_data()
if df is None:
    st.stop()


def point(indicator, breakdown="all", area=NEWHAM_CODE):
    r = latest_period(df[(df.indicator == indicator) & (df.breakdown == breakdown)])
    r = r[r.area_code == area]
    return None if r.empty else r.iloc[0]


def tile(col, title, indicator, breakdown="all"):
    r, london = point(indicator, breakdown), point(indicator, breakdown, LONDON_CODE)
    if r is not None:
        col.metric(
            title,
            fmt(r["value"], r["unit"]),
            help=f"London: {fmt(london['value'], london['unit'])}" if london is not None else None,
        )


c = st.columns(4)
tile(c[0], "Households in TA", "ta_households")
tile(c[1], "Share of all households", "ta_households_pct_of_households")
tile(c[2], "Households with children", "ta_households_with_children")
tile(c[3], "Children in TA", "ta_children")

others = st.multiselect(
    "Compare with up to three other boroughs",
    [n for n in borough_names(df) if n != "Newham"],
    default=[],
    max_selections=viz.MAX_EXTRA_AREAS,
)
areas = ["Newham", "London", "England", *others]

tabs = st.tabs(
    [
        "Household type",
        "Age of main applicant",
        "Ethnicity",
        "Children",
        "Duty owed",
        "Pregnancy (priority need)",
    ]
)


def share_text(indicator, breakdown):
    n, lon = point(indicator, breakdown), point(indicator, breakdown, LONDON_CODE)
    if n is None or lon is None:
        return ""
    return f"Newham {fmt(n['value'], 'percent')}, London {fmt(lon['value'], 'percent')}."


with tabs[0]:
    chart_title(
        "Household composition, share of households in TA",
        "Female lone parents are the largest group. "
        + share_text("ta_households_by_composition_share", "one_adult_female_with_children"),
    )
    compare_breakdown(
        df,
        "ta_households_by_composition_share",
        areas,
        order=[
            "one_adult_female_with_children",
            "one_adult_male_with_children",
            "one_adult_other_sex_with_children",
            "two_adults_with_children",
            "three_plus_adults_with_children",
            "adult_only",
            "other_or_not_known",
        ],
    )
    caveat("ta_households_by_composition")
    source_footnote(df[df.indicator == "ta_households_by_composition"])

with tabs[1]:
    chart_title(
        "Age of main applicant, share of households in TA",
        "Aged 45 or over: Newham's applicants skew a little older than London's.",
    )
    compare_breakdown(
        df,
        "ta_households_by_age_of_main_applicant_share",
        areas,
        order=[
            "16_to_17",
            "18_to_24",
            "25_to_34",
            "35_to_44",
            "45_to_54",
            "55_to_64",
            "65_to_74",
            "75_plus",
            "not_known",
        ],
    )
    caveat("ta_households_by_age_of_main_applicant")
    source_footnote(df[df.indicator == "ta_households_by_age_of_main_applicant"])

with tabs[2]:
    nk = point("ta_households_by_ethnicity_share", "not_known")
    nk_london = point("ta_households_by_ethnicity_share", "not_known", LONDON_CODE)
    if nk is not None:
        st.warning(
            f"Ethnicity is **not known for {fmt(nk['value'], 'percent')}** of Newham's TA "
            "households"
            + (f" (London {fmt(nk_london['value'], 'percent')})" if nk_london is not None else "")
            + ". Shares below are of households whose ethnicity is known. Without the borough's "
            "population mix they say nothing about over- or under-representation."
        )
    detail = st.toggle("Show detailed categories", value=False)
    base = "ta_households_by_ethnicity_detail" if detail else "ta_households_by_ethnicity"
    chart_title("Ethnicity of main applicant, share of known", "")
    compare_breakdown(df, f"{base}_share_of_known", areas)
    caveat(base)
    source_footnote(df[df.indicator == base])

with tabs[3]:
    kids, under18 = point("ta_children"), point("ta_children_under_18")
    families = point("ta_households_with_children")
    by_age = latest_period(
        df[(df.indicator == "ta_children_by_age") & (df.area_code == NEWHAM_CODE)]
    )
    k = st.columns(4)
    if kids is not None:
        k[0].metric("Children in TA (TA1)", fmt(kids["value"], "children"))
    if under18 is not None:
        k[1].metric("People under 18 (TA8)", fmt(under18["value"], "children"))
    if families is not None:
        k[2].metric("Families with children", fmt(families["value"], "households"))
    if not by_age.empty:
        by_age = by_age.assign(
            age=by_age.breakdown.str.removeprefix("age_").astype(int)
        ).sort_values("age")
        u5 = point("ta_children_under_5")
        if u5 is not None:
            k[3].metric("Children under 5 (TA8)", fmt(u5["value"], "children"))
        chart_title(
            "Newham: people under 18 in TA, by single year of age",
            "About 2 children per family, as in London and England. Very few babies (age 0) "
            "are recorded, a pattern seen in every borough.",
        )
        peak = by_age.loc[by_age.value.idxmax()]
        fig = go.Figure(
            go.Bar(
                x=by_age["age"],
                y=by_age["value"],
                marker={"color": viz.accent()},
                width=0.6,
                text=[
                    fmt(v, "children") if a == peak.age else ""
                    for a, v in zip(by_age.age, by_age.value, strict=True)
                ],
                textposition="outside",
                textfont={"color": viz.tok("ink"), "size": 11},
                cliponaxis=False,
                hovertemplate="Age %{x}: %{y:,.0f} children<extra></extra>",
            )
        )
        viz.style(fig, height=320, legend=False, x_title="Age", y_title="children")
        fig.update_xaxes(dtick=1)
        st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})
        table_view(by_age[["age", "value"]].rename(columns={"age": "Age", "value": "Children"}))
    st.caption(
        "TA1 and TA8 are separate MHCLG counts and differ slightly; they are not reconciled here."
    )
    if others and st.toggle("Compare the age mix with the boroughs selected above", value=False):
        compare_breakdown(
            df,
            "ta_children_by_age_share",
            ["Newham", *others],
            order=[f"age_{a}" for a in range(18)],
        )
        st.caption("Each bar is one year of age as a share of that borough's under-18s in TA.")
    caveat("ta_children_by_age")
    source_footnote(df[df.indicator == "ta_children_by_age"])

with tabs[4]:
    chart_title(
        "Duty under which households are housed, share of households in TA",
        share_text("ta_households_by_duty_share", "s193_main_duty").replace(".", "")
        + " are owed the main duty.",
    )
    compare_breakdown(df, "ta_households_by_duty_share", areas)
    caveat("ta_households_by_duty")
    source_footnote(df[df.indicator == "ta_households_by_duty"])

with tabs[5]:
    st.warning(
        "**This is not a count of pregnant households in TA.** The TA tables have no pregnancy "
        "field. Table MD3 records the *priority need* of households newly owed the main duty in "
        "the quarter. 'Pregnant' counts only households where pregnancy is the recorded reason, "
        "so pregnant women in families recorded under 'dependent children' are missed."
    )
    preg = point("main_duty_owed_by_priority_need", "pregnant")
    total = point("main_duty_owed_total")
    if preg is not None and total is not None:
        st.metric(
            "Newham, January to March 2026: newly owed the main duty, priority need pregnancy",
            f"{fmt(preg['value'], 'households')} of {fmt(total['value'], 'households')}",
        )
    chart_title(
        "Priority need of households newly owed the main duty, share",
        share_text("main_duty_owed_by_priority_need_share", "pregnant").replace(".", "")
        + " for pregnancy.",
    )
    compare_breakdown(
        df,
        "main_duty_owed_by_priority_need_share",
        areas,
        order=[
            "dependent_children",
            "children_other_priority_need",
            "pregnant",
            "vulnerable",
            "emergency",
        ],
    )
    caveat("main_duty_owed_by_priority_need")
    source_footnote(df[df.indicator == "main_duty_owed_by_priority_need"])

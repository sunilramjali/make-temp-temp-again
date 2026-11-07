import streamlit as st

from components import (
    DESCRIPTIVE,
    borough_names,
    caveat,
    compare_breakdown,
    label,
    latest_period,
    need_data,
    source_footnote,
)
from ta_london.geography import NEWHAM_CODE

st.set_page_config(page_title="Demographics", layout="wide")
st.title("Who is in temporary accommodation?")
st.write(
    "Household type, age, ethnicity and children in temporary accommodation (TA), "
    "Newham compared with London and England. Percentages are shares of households (or children) "
    "in each group, calculated in the pipeline."
)
st.caption(DESCRIPTIVE)

df = need_data()
if df is None:
    st.stop()

others = st.multiselect(
    "Add boroughs to compare",
    [n for n in borough_names(df) if n != "Newham"],
    default=[],
)
areas = ["Newham", "London", "England", *others]


def point(indicator, breakdown="all", area=NEWHAM_CODE):
    r = latest_period(df[(df.indicator == indicator) & (df.breakdown == breakdown)])
    r = r[r.area_code == area]
    return None if r.empty else r.iloc[0]


# Headline numbers for Newham
cols = st.columns(4)
for col, (ind, fmt) in zip(
    cols,
    [
        ("ta_households", "{:,.0f}"),
        ("ta_households_per_1000", "{:,.1f}"),
        ("ta_households_with_children", "{:,.0f}"),
        ("ta_children", "{:,.0f}"),
    ],
    strict=True,
):
    r = point(ind)
    london = point(ind, area="E12000007")
    if r is not None:
        col.metric(
            label(ind),
            fmt.format(r["value"]),
            help=f"London: {fmt.format(london['value'])}" if london is not None else None,
        )

tabs = st.tabs(["Household type", "Age of main applicant", "Ethnicity", "Children", "Duty owed"])

with tabs[0]:
    st.subheader("Household composition")
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
    st.subheader("Age of main applicant")
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
    st.subheader("Ethnicity of main applicant")
    nk = point("ta_households_by_ethnicity_share", "not_known")
    nk_london = point("ta_households_by_ethnicity_share", "not_known", "E12000007")
    if nk is not None:
        st.warning(
            f"Ethnicity is **not known for {nk['value']:.1f}%** of Newham's TA households"
            + (f" (London: {nk_london['value']:.1f}%)" if nk_london is not None else "")
            + ". The charts below show shares of households whose ethnicity is known. "
            "They say nothing about over- or under-representation without the borough's "
            "population mix, which is not in this data."
        )
    detail = st.toggle("Show detailed categories", value=False)
    base = "ta_households_by_ethnicity_detail" if detail else "ta_households_by_ethnicity"
    compare_breakdown(df, f"{base}_share_of_known", areas, horizontal=detail)
    caveat(base)
    source_footnote(df[df.indicator == base])

with tabs[3]:
    st.subheader("Children by age")
    st.write(
        "People under 18 in TA by single year of age, as a share of all under-18s in TA "
        "(London and England are not published for this table)."
    )
    compare_breakdown(
        df,
        "ta_children_by_age_share",
        [a for a in areas if a not in ("London", "England")],
        order=[f"age_{a}" for a in range(18)],
    )
    caveat("ta_children_by_age")
    source_footnote(df[df.indicator == "ta_children_by_age"])

with tabs[4]:
    st.subheader("Duty owed")
    compare_breakdown(df, "ta_households_by_duty_share", areas)
    caveat("ta_households_by_duty")
    source_footnote(df[df.indicator == "ta_households_by_duty"])

st.info(
    "**Pregnant households are not identified in these tables.** There is no pregnancy field in "
    "the MHCLG TA tables, so they can't be shown here. See `docs/evidence_gaps.md`."
)

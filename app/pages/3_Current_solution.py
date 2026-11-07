import streamlit as st

from components import (
    DESCRIPTIVE,
    borough_names,
    caveat,
    compare_breakdown,
    doc_section,
    latest_period,
    need_data,
    pretty,
    source_footnote,
)
from ta_london.geography import NEWHAM_CODE

st.set_page_config(page_title="Current solution", layout="wide")
st.title("Where families are placed, and what Newham's policies offer")
st.write(
    "How families in temporary accommodation (TA) are housed now, how long they have been there, "
    "and the policies that shape where they are placed."
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


oa = point("ta_households_out_of_area_share")
oa_london = point("ta_households_out_of_area_share", area="E12000007")
nightly = point("ta_families_by_accommodation_type_share", "nightly_paid")
nightly_london = point("ta_families_by_accommodation_type_share", "nightly_paid", "E12000007")
c1, c2 = st.columns(2)
if oa is not None:
    c1.metric(
        "Newham TA households placed out of area",
        f"{oa['value']:.1f}%",
        help=f"London: {oa_london['value']:.1f}%" if oa_london is not None else None,
    )
if nightly is not None:
    c2.metric(
        "Newham families in nightly-paid accommodation",
        f"{nightly['value']:.1f}%",
        help=f"London: {nightly_london['value']:.1f}%" if nightly_london is not None else None,
    )

tabs = st.tabs(
    [
        "Accommodation type",
        "Length of stay",
        "How households leave TA",
        "Out of area",
        "Policies in brief",
    ]
)

with tabs[0]:
    st.subheader("Families with children, by type of accommodation")
    compare_breakdown(
        df,
        "ta_families_by_accommodation_type_share",
        areas,
        order=["nightly_paid", "private_sector", "la_ha_stock", "bnb", "hostel", "other"],
    )
    caveat("ta_families_by_accommodation_type")
    source_footnote(df[df.indicator == "ta_families_by_accommodation_type"])
    st.subheader("Out of area")
    compare_breakdown(df, "ta_households_out_of_area_share", areas)
    caveat("ta_households_out_of_area_share")

with tabs[1]:
    st.subheader("Time families have spent in TA, by accommodation type")
    types = [
        "nightly_paid",
        "la_ha_stock",
        "private_sector",
        "bnb",
        "hostel",
        "other",
    ]
    chosen = st.selectbox("Accommodation type", types, format_func=pretty)
    bands = [
        "less_than_6_months",
        "6_to_12_months",
        "1_to_2_years",
        "2_to_5_years",
        "5_plus_years",
    ]
    compare_breakdown(
        df,
        "ta_families_length_of_stay_share",
        areas,
        order=[f"{chosen}__{b}" for b in bands],
    )
    st.caption(
        "Shares are within the chosen type. Small types are often suppressed in the source "
        "(shown as 'no value')."
    )
    caveat("ta_families_length_of_stay")
    st.subheader("Median days in TA, all households still in TA, by type")
    med = latest_period(
        df[(df.indicator == "ta_length_of_stay_median_days") & df.area_name.isin(areas)]
    )
    if not med.empty:
        piv = med.pivot_table(index="breakdown", columns="area_name", values="value")
        piv.index = [pretty(i) for i in piv.index]
        st.dataframe(piv.round(0), width="stretch")
    caveat("ta_length_of_stay_median_days")
    source_footnote(df[df.indicator == "ta_families_length_of_stay"])

with tabs[2]:
    st.subheader("Why the main homelessness duty ended, January to March 2026")
    st.write(
        "Ending the main duty is the main way households leave TA. This is one quarter's flow, "
        "so small boroughs can swing a lot between quarters."
    )
    ended = point("main_duty_ended_total")
    if ended is not None:
        prs = point("main_duty_ended_by_reason", "prs_offer_accepted")
        social = point("main_duty_ended_by_reason", "social_offer_accepted")
        c1, c2, c3 = st.columns(3)
        c1.metric("Newham: main duty ended (quarter)", f"{ended['value']:,.0f}")
        if prs is not None:
            c2.metric("of which private rented offer accepted", f"{prs['value']:,.0f}")
        if social is not None:
            c3.metric("of which social housing offer accepted", f"{social['value']:,.0f}")
    compare_breakdown(
        df,
        "main_duty_ended_by_reason_share",
        areas,
        order=[
            "social_offer_accepted",
            "social_offer_refused",
            "prs_offer_accepted",
            "prs_offer_refused",
            "refused_ta_withdrew_or_lost_contact",
            "ceased_eligible",
            "intentionally_homeless_from_ta",
            "voluntarily_left_ta",
            "not_known",
        ],
        horizontal=True,
    )
    caveat("main_duty_ended_by_reason")
    source_footnote(df[df.indicator == "main_duty_ended_by_reason"])

with tabs[3]:
    st.subheader("Where out-of-area households are placed (31 March 2026)")
    dest = latest_period(
        df[(df.indicator == "ta_out_of_area_by_destination") & df.area_name.isin(areas)]
    )
    if not dest.empty:
        piv = dest.pivot_table(index="breakdown", columns="area_name", values="value")
        piv.index = [pretty(i) for i in piv.index]
        st.dataframe(piv.fillna(0).astype(int), width="stretch")
        st.caption("Counts of households by destination region (TA9).")
    caveat("ta_out_of_area_by_destination")
    st.subheader("Out-of-area households by type of accommodation")
    compare_breakdown(
        df,
        "ta_out_of_area_by_accommodation_type_share",
        areas,
        order=[
            "nightly_paid",
            "private_sector",
            "bnb",
            "la_ha_stock",
            "hostel",
            "other",
            "no_accommodation_secured",
        ],
    )
    st.subheader("Out-of-area households by household type")
    compare_breakdown(
        df,
        "ta_out_of_area_by_composition_share",
        areas,
        order=[
            "one_adult_female_with_children",
            "one_adult_male_with_children",
            "two_adults_with_children",
            "three_plus_adults_with_children",
            "adult_only",
            "other_or_not_known",
        ],
    )
    source_footnote(df[df.indicator == "ta_out_of_area_by_accommodation_type"])

with tabs[4]:
    section = doc_section("docs/newham_evidence_brief.md", "4.")
    if section:
        st.markdown(section)
    else:
        st.info("`docs/newham_evidence_brief.md` not found.")
    st.caption(
        "This records what is offered in published policy. Uptake and outcomes are not shown: "
        "none was found. See the Policies page for the services map and policy documents."
    )

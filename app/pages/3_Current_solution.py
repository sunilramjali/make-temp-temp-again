import streamlit as st

import viz
from components import (
    borough_names,
    caveat,
    chart_title,
    compare_breakdown,
    doc_section,
    fmt,
    latest_period,
    need_data,
    page_header,
    pretty,
    source_footnote,
)
from ta_london.geography import NEWHAM_CODE

st.set_page_config(page_title="Current solution · TA in London", layout="wide")
page_header(
    "Where families are placed, and how they leave",
    "How families in temporary accommodation (TA) are housed, how long they have been there, "
    "how the homelessness duty ends, and what Newham's policies offer.",
)

df = need_data()
if df is None:
    st.stop()

others = st.multiselect(
    "Compare with up to three other boroughs",
    [n for n in borough_names(df) if n != "Newham"],
    default=[],
    max_selections=viz.MAX_EXTRA_AREAS,
)
areas = ["Newham", "London", "England", *others]


def point(indicator, breakdown="all", area=NEWHAM_CODE):
    r = latest_period(df[(df.indicator == indicator) & (df.breakdown == breakdown)])
    r = r[r.area_code == area]
    return None if r.empty else r.iloc[0]


def tile(col, title, indicator, breakdown="all"):
    r, london = point(indicator, breakdown), point(indicator, breakdown, "E12000007")
    if r is not None:
        col.metric(
            title,
            fmt(r["value"], r["unit"]),
            help=f"London: {fmt(london['value'], london['unit'])}" if london is not None else None,
        )


c = st.columns(4)
tile(c[0], "Families in nightly-paid", "ta_families_by_accommodation_type_share", "nightly_paid")
tile(c[1], "Placed out of area", "ta_households_out_of_area_share")
tile(c[2], "Duties ended (quarter)", "main_duty_ended_total")
tile(c[3], "Ended via private renting", "main_duty_ended_by_reason_share", "prs_offer_accepted")

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
    chart_title(
        "Families with children in TA, by type of accommodation",
        "Nightly-paid, privately managed homes are the main form of TA for Newham families.",
    )
    compare_breakdown(
        df,
        "ta_families_by_accommodation_type_share",
        areas,
        order=["nightly_paid", "private_sector", "la_ha_stock", "bnb", "hostel", "other"],
    )
    caveat("ta_families_by_accommodation_type")
    source_footnote(df[df.indicator == "ta_families_by_accommodation_type"])
    chart_title("Households in TA placed in another council's area", "")
    compare_breakdown(df, "ta_households_out_of_area_share", areas)
    caveat("ta_households_out_of_area_share")

with tabs[1]:
    chart_title(
        "How long families have been in TA, within each accommodation type",
        "Most Newham families in nightly-paid TA have been there more than a year.",
    )
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
    chart_title("Median days in TA, by type", "All households still in TA at 31 March 2026.")
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
    chart_title(
        "Why the main homelessness duty ended, January to March 2026",
        "In this quarter, private rented offers ended more of Newham's 82 duties than social "
        "housing offers; in London and England it was the other way round. One quarter, small "
        "numbers.",
    )
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
    chart_title("Where out-of-area households are placed", "Counts at 31 March 2026, by region.")
    dest = latest_period(
        df[(df.indicator == "ta_out_of_area_by_destination") & df.area_name.isin(areas)]
    )
    if not dest.empty:
        piv = dest.pivot_table(index="breakdown", columns="area_name", values="value")
        piv.index = [pretty(i) for i in piv.index]
        st.dataframe(piv.fillna(0).astype(int), width="stretch")
        st.caption("Counts of households by destination region (TA9).")
    caveat("ta_out_of_area_by_destination")
    chart_title("Out-of-area households by type of accommodation", "")
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
    chart_title("Out-of-area households by household type", "")
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

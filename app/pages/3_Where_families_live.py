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

st.set_page_config(page_title="Where families live · TA in London", layout="wide")
page_header(
    "Where families live, and how they move on",
    "The kinds of temporary accommodation (TA) families live in, how long they stay, how they "
    "move on to a settled home, and what Newham's policies offer.",
)

df = need_data()
if df is None:
    st.stop()

others = st.multiselect(
    "Add up to three boroughs to compare",
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
tile(
    c[0],
    "Families in nightly-paid homes",
    "ta_families_by_accommodation_type_share",
    "nightly_paid",
)
tile(c[1], "Housed outside Newham", "ta_households_out_of_area_share")
tile(c[2], "Cases closed, Jan to Mar 2026", "main_duty_ended_total")
tile(c[3], "Moved on to private renting", "main_duty_ended_by_reason_share", "prs_offer_accepted")

tabs = st.tabs(
    [
        "Type of home",
        "Time spent in TA",
        "Moving on",
        "Housed outside the borough",
        "Newham's policies",
    ]
)

with tabs[0]:
    chart_title(
        "Families with children in TA, by type of home",
        "Most Newham families are in homes the council rents from private owners by the night.",
    )
    compare_breakdown(
        df,
        "ta_families_by_accommodation_type_share",
        areas,
        order=["nightly_paid", "private_sector", "la_ha_stock", "bnb", "hostel", "other"],
    )
    caveat("ta_families_by_accommodation_type")
    source_footnote(df[df.indicator == "ta_families_by_accommodation_type"])
    chart_title("Households in TA housed outside their own borough", "")
    compare_breakdown(df, "ta_households_out_of_area_share", areas)
    caveat("ta_households_out_of_area_share")

with tabs[1]:
    chart_title(
        "How long families have been in TA, for each type of home",
        "Most Newham families in nightly-paid homes have been there for more than a year.",
    )
    types = [
        "nightly_paid",
        "la_ha_stock",
        "private_sector",
        "bnb",
        "hostel",
        "other",
    ]
    chosen = st.selectbox("Type of home", types, format_func=pretty)
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
        "Shares add up to 100% within the chosen type of home. For less common types, the "
        "government often doesn't publish figures because the numbers are small."
    )
    caveat("ta_families_length_of_stay")
    chart_title(
        "Typical number of days in TA, by type of home",
        "The middle value (median) for all households still in TA on 31 March 2026.",
    )
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
        "How cases were closed, January to March 2026",
        "In these three months, more of Newham's 82 closed cases ended with a private rented "
        "home than a social home. In London and England it was the other way round. The numbers "
        "are small, so this may not be typical.",
    )
    st.write(
        "Most families leave temporary accommodation when the council closes their case (ends "
        "its 'main duty'), usually because they accept a settled home. These are three months of "
        "figures, so smaller boroughs can change a lot from one quarter to the next."
    )
    ended = point("main_duty_ended_total")
    if ended is not None:
        prs = point("main_duty_ended_by_reason", "prs_offer_accepted")
        social = point("main_duty_ended_by_reason", "social_offer_accepted")
        c1, c2, c3 = st.columns(3)
        c1.metric("Newham: cases closed", f"{ended['value']:,.0f}")
        if prs is not None:
            c2.metric("Accepted a private rented home", f"{prs['value']:,.0f}")
        if social is not None:
            c3.metric("Accepted a social home", f"{social['value']:,.0f}")
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
    chart_title(
        "Where households housed outside their borough are living",
        "Number of households on 31 March 2026, by region.",
    )
    dest = latest_period(
        df[(df.indicator == "ta_out_of_area_by_destination") & df.area_name.isin(areas)]
    )
    if not dest.empty:
        piv = dest.pivot_table(index="breakdown", columns="area_name", values="value")
        piv.index = [pretty(i) for i in piv.index]
        st.dataframe(piv.fillna(0).astype(int), width="stretch")
        st.caption("Number of households in each region.")
    caveat("ta_out_of_area_by_destination")
    chart_title("Households housed outside their borough, by type of home", "")
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
    chart_title("Households housed outside their borough, by type of household", "")
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
        st.info("The policy summary isn't available yet.")
    st.caption(
        "This shows what Newham's published policies offer. We found no figures on how many "
        "families use these services or whether they help. See the Council support page for "
        "more."
    )

import streamlit as st

from components import fmt, latest_period, load_source_register, need_data, page_header
from ta_london.geography import LONDON_CODE, NEWHAM_CODE

st.set_page_config(page_title="Temporary accommodation in London", layout="wide")
page_header(
    "Temporary accommodation for families in London",
    "Families with children and pregnant women in temporary accommodation (TA) across London's "
    "33 boroughs, with Newham as the case study. Official, published data only.",
)

df = need_data()
if df is None:
    st.stop()


def point(indicator, breakdown="all", area=NEWHAM_CODE, period=None):
    sub = df[(df.indicator == indicator) & (df.breakdown == breakdown) & (df.area_code == area)]
    sub = sub[sub.period == period] if period else latest_period(sub)
    return None if sub.empty else sub.iloc[0]


share = point("ta_households_pct_of_households")
share_london = point("ta_households_pct_of_households", area=LONDON_CODE)
if share is not None:
    st.markdown(
        '<p style="font-size:3.6rem;font-weight:650;line-height:1.0;margin:0.5rem 0 0.2rem 0">'
        f"{fmt(share['value'], 'percent')}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:1.02rem;opacity:0.8;margin-bottom:1.1rem;max-width:46rem">'
        "of all households in Newham were in temporary accommodation on "
        f"31 March 2026, the highest share in London (London overall "
        f"{fmt(share_london['value'], 'percent')}).</p>",
        unsafe_allow_html=True,
    )

tiles = [
    ("Households in TA", point("ta_households"), "31 March 2026"),
    ("Children in TA", point("ta_children"), "31 March 2026"),
    ("On the housing register", point("housing_register_households"), "31 March 2025"),
    ("New social lettings", point("social_lettings_total"), "2024/25"),
]
cols = st.columns(4)
for col, (title, r, when) in zip(cols, tiles, strict=True):
    if r is not None:
        col.metric(title, fmt(r["value"], r["unit"]), help=f"Newham, {when}")

st.subheader("Key findings")
nightly = point("ta_families_by_accommodation_type_share", "nightly_paid")
five_plus = point("ta_families_length_of_stay", "nightly_paid__5_plus_years")
prs = point("main_duty_ended_by_reason_share", "prs_offer_accepted")
ended = point("main_duty_ended_total")
social = point("main_duty_ended_by_reason_share", "social_offer_accepted")
oa = point("ta_households_out_of_area_share")
gap = point("rent_gap_weekly")
findings = []
if nightly is not None and five_plus is not None:
    findings.append(
        f"**{fmt(nightly['value'], 'percent')} of Newham families in TA are in nightly-paid, "
        f"privately managed homes**, and {fmt(five_plus['value'], 'households')} of those "
        "families have been there five years or more."
    )
if oa is not None:
    findings.append(
        f"**{fmt(oa['value'], 'percent')} of Newham's TA households are placed outside the "
        "borough**, most of them elsewhere in London."
    )
if prs is not None and social is not None and ended is not None:
    findings.append(
        "**In January to March 2026, more Newham households left the homelessness duty through "
        "private renting than through social housing**: "
        f"{fmt(prs['value'], 'percent')} of {fmt(ended['value'], 'households')} ended duties were "
        f"accepted private rented offers, {fmt(social['value'], 'percent')} social housing offers. "
        "Across London it was the other way round. This is one quarter with small numbers, so it "
        "may not be typical."
    )
relet = point("social_relet_rate")
if relet is not None:
    findings.append(
        "**Social housing is scarce and turns over slowly.** Newham's housing register has grown "
        f"every year since 2018, while it re-let {fmt(relet['value'], 'percent')} of its social "
        "homes in 2024/25."
    )
if gap is not None:
    findings.append(
        f"**Private rents are far above social rents**: about {fmt(gap['value'], 'gbp_per_week')} "
        "a week more on average, the gap a family must bridge to leave TA for private renting."
    )
findings.append(
    "**Pregnant households are not counted in the TA statistics.** The nearest measure (pregnancy "
    "as the priority need for new acceptances) undercounts them."
)
st.markdown("\n".join(f"- {f}" for f in findings))
st.caption(
    "Descriptive findings from official statistics. They show patterns, not causes. "
    "Definitions and caveats are on each page."
)

st.subheader("Explore")
g = st.columns(5)
pages = [
    ("pages/1_London_boroughs.py", "London boroughs", "Rank all 33 boroughs; London since 2002."),
    ("pages/2_Demographics.py", "Demographics", "Who is in TA: households, age, children."),
    ("pages/3_Current_solution.py", "Current solution", "Placements, length of stay, exits."),
    ("pages/4_Social_housing.py", "Social housing", "Register, lettings, supply, rents."),
    ("pages/5_Policies.py", "Policies", "Services offered vs evidence they work."),
]
for col, (path, title, blurb) in zip(g, pages, strict=True):
    with col:
        st.page_link(path, label=title)
        st.caption(blurb)

with st.expander("Data sources and freshness"):
    freshness = (
        df.groupby("source_id")
        .agg(indicators=("indicator", "nunique"), latest=("period_end", "max"))
        .reset_index()
    )
    register = load_source_register()
    if not register.empty:
        freshness = freshness.merge(
            register[["source_id", "title", "publisher", "reference_period"]],
            on="source_id",
            how="left",
        )
        freshness = freshness[
            ["title", "publisher", "reference_period", "indicators", "latest", "source_id"]
        ]
    st.dataframe(freshness, hide_index=True, width="stretch")
    st.caption("Full list with links and how far each was checked: Policies page, Source links.")

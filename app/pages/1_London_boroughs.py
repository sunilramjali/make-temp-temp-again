import streamlit as st

from components import (
    caveat,
    chart_title,
    indicator_explorer,
    load_data,
    source_footnote,
    stacked_trend,
    trend,
)

st.set_page_config(page_title="London boroughs", layout="wide")

indicator_explorer(
    "London boroughs",
    "See how London's 33 boroughs compare on temporary accommodation (TA), social housing "
    "waiting lists, new lettings and new council homes. Choose what to compare and when. "
    "Measures marked 'yearly average' are averaged over four quarters, so they differ slightly "
    "from the single-day count on 31 March 2026.",
    [
        "ta_households_pct_of_households",
        "ta_households_with_children_pct_of_households",
        "ta_households",
        "ta_households_per_1000",
        "ta_households_avg4q",
        "ta_households_per_1000_avg4q",
        "ta_households_with_children",
        "ta_households_with_children_per_1000_avg4q",
        "ta_children",
        "ta_households_out_of_area",
        "ta_households_out_of_area_share",
        "ta_households_out_of_area_per_1000",
        "ta_bnb_with_children",
        "main_duty_owed_total",
        "main_duty_ended_total",
        "housing_register_households",
        "social_lettings_total",
        "social_relet_rate",
        "social_relet_rent_weekly",
        "market_rent_weekly",
        "council_homes_started_gla",
        "council_homes_completed_gla",
    ],
)

df = load_data()
if df is not None and not df[df.indicator == "ta_households_avg4q"].empty:
    st.divider()
    st.header("How London has changed, 2002 to 2025")
    chart_title(
        "Households in temporary accommodation in London, yearly average",
        "Up from 48,678 in 2002 to 74,860 in 2025. The line in 2018/19 marks a change in how "
        "the government collects the figures.",
    )
    trend(df, "ta_households_avg4q", ["London"])
    chart_title(
        "London households in temporary accommodation, by type of home",
        "Homes rented from private owners by the night are now the most common type.",
    )
    stacked_trend(
        df,
        "ta_households_by_accommodation_type_avg4q",
        "London",
        order=["nightly_paid", "private_sector", "la_ha_stock", "bnb", "hostel", "other"],
    )
    caveat("ta_households_by_accommodation_type_avg4q")
    source_footnote(df[df.indicator == "ta_households_by_accommodation_type_avg4q"])

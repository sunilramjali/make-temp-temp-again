import streamlit as st

from components import caveat, indicator_explorer, load_data, source_footnote, stacked_trend, trend

st.set_page_config(page_title="London boroughs", layout="wide")

indicator_explorer(
    "London boroughs",
    "Borough comparison of temporary accommodation (TA), the housing register, social lettings "
    "and new council homes. Newham is highlighted in red. Choose an indicator and period. "
    "Indicators ending '(4-quarter average)' are Trust for London averages, a different measure "
    "from the MHCLG 31 March 2026 snapshot.",
    [
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
    st.header("London over time, 2002 to 2025")
    st.write(
        "London-wide households in TA, average of four quarters each year (Trust for London, "
        "from MHCLG). Borough-level history is not in the data yet."
    )
    trend(df, "ta_households_avg4q", ["London"])
    stacked_trend(
        df,
        "ta_households_by_accommodation_type_avg4q",
        "London",
        order=["nightly_paid", "private_sector", "la_ha_stock", "bnb", "hostel", "other"],
    )
    caveat("ta_households_by_accommodation_type_avg4q")
    source_footnote(df[df.indicator == "ta_households_by_accommodation_type_avg4q"])

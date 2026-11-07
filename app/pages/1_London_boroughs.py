import streamlit as st

from components import indicator_explorer

st.set_page_config(page_title="London boroughs", layout="wide")

indicator_explorer(
    "London boroughs",
    "Borough comparison of temporary accommodation (TA), the housing register and social "
    "lettings. Newham is highlighted in red. Choose an indicator and period.",
    [
        "ta_households",
        "ta_households_per_1000",
        "ta_households_with_children",
        "ta_children",
        "ta_households_out_of_area",
        "ta_households_out_of_area_share",
        "ta_bnb_with_children",
        "housing_register_households",
        "social_lettings_total",
        "social_relet_rate",
        "social_relet_rent_weekly",
        "market_rent_weekly",
    ],
)

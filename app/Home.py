import streamlit as st

from components import NO_DATA_MESSAGE, caveat_box, load_data, load_source_register

st.set_page_config(page_title="TA in London", layout="wide")

st.title("Temporary accommodation for families in London")
st.write(
    "A research dashboard on families with children and pregnant women in temporary "
    "accommodation across London, with Newham as a case study."
)
caveat_box()

st.subheader("Data freshness")
df = load_data()
if df is None or df.empty:
    st.warning(NO_DATA_MESSAGE)
else:
    freshness = (
        df.groupby("source_id")["period_end"].max().rename("latest period end").reset_index()
    )
    st.dataframe(freshness, hide_index=True)

st.subheader("Registered sources")
register = load_source_register()
if register.empty:
    st.write("No datasets registered yet in `data/sources.csv`.")
else:
    st.dataframe(
        register[["source_id", "title", "publisher", "reference_period", "date_accessed"]],
        hide_index=True,
    )

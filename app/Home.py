import streamlit as st

from components import DESCRIPTIVE, label, load_source_register, need_data

st.set_page_config(page_title="TA in London", layout="wide")

st.title("Temporary accommodation for families in London")
st.write(
    "A research dashboard on families with children and pregnant women in temporary "
    "accommodation (TA) across London, with Newham as a case study."
)
st.caption(DESCRIPTIVE)

st.markdown(
    """
**Pages**
- **London boroughs**: rank the 33 boroughs on TA, the housing register and social lettings.
- **Demographics**: household type, age, ethnicity and children, Newham vs London and England.
- **Current solution**: where families are placed, how long they stay, and Newham policy in brief.
- **Social housing**: register, lettings, churn and rents, and the barriers to entry.
- **Policies**: services map, policy documents, the evidence brief and source links.
"""
)

st.subheader("Data freshness")
df = need_data()
if df is not None:
    freshness = (
        df.groupby("source_id")
        .agg(
            indicators=("indicator", "nunique"),
            earliest=("period_end", "min"),
            latest=("period_end", "max"),
            rows=("value", "size"),
        )
        .reset_index()
    )
    st.dataframe(freshness, hide_index=True)
    st.caption(
        f"{df['indicator'].nunique()} indicators, {df['area_code'].nunique()} areas "
        f"(33 London boroughs plus London and England totals where published). "
        f"Example: {label('ta_households')}."
    )

st.subheader("Registered sources")
register = load_source_register()
if register.empty:
    st.write("No datasets registered yet in `data/sources.csv`.")
else:
    st.dataframe(
        register[["source_id", "title", "publisher", "reference_period", "date_accessed"]],
        hide_index=True,
    )

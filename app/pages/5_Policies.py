import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import caveat_box
from ta_london.paths import SERVICES_MAP
from ta_london.services import add_evidence_states, list_policy_documents, load_services

st.title("Policies and services")
st.write(
    "What each borough offers, kept separate from evidence that a service is used or works. "
    "A published scheme is not evidence that it works."
)
caveat_box()

tab_matrix, tab_table, tab_docs = st.tabs(["Matrix", "Services table", "Policy documents"])

services = add_evidence_states(load_services()) if SERVICES_MAP.exists() else pd.DataFrame()

STATE_LABELS = {
    0: "Not recorded",
    1: "Offered",
    2: "Offered + uptake evidence",
    3: "Offered + outcome evidence",
}


def state(row) -> int:
    if row["has_outcome_evidence"]:
        return 3
    if row["has_uptake_evidence"]:
        return 2
    return 1 if row["offered"] else 0


with tab_matrix:
    if services.empty:
        st.warning(
            "`policy/services_map.csv` has no rows yet. Add rows (one per borough and service), "
            "citing the policy document and section."
        )
    else:
        # Highest recorded state per borough x category; text shows each state separately.
        services = services.assign(state=services.apply(state, axis=1))
        grid = services.pivot_table(
            index="borough", columns="service_category", values="state", aggfunc="max"
        ).fillna(0)
        fig = go.Figure(
            go.Heatmap(
                z=grid.values,
                x=list(grid.columns),
                y=list(grid.index),
                zmin=0,
                zmax=3,
                colorscale=[
                    [0.0, "#eeeeee"],
                    [0.25, "#eeeeee"],
                    [0.26, "#9ecae1"],
                    [0.5, "#9ecae1"],
                    [0.51, "#4292c6"],
                    [0.75, "#4292c6"],
                    [0.76, "#08306b"],
                    [1.0, "#08306b"],
                ],
                showscale=False,
                hovertemplate="%{y} / %{x}<extra></extra>",
            )
        )
        fig.update_layout(height=max(300, 40 * len(grid)), yaxis_autorange="reversed")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Grey: nothing recorded. Light blue: offered. Mid blue: offered with uptake evidence. "
            "Dark blue: offered with outcome evidence."
        )

with tab_table:
    if services.empty:
        st.write("No rows yet.")
    else:
        boroughs = st.multiselect("Borough", sorted(services["borough"].unique()))
        cats = st.multiselect("Service category", sorted(services["service_category"].unique()))
        view = services
        if boroughs:
            view = view[view["borough"].isin(boroughs)]
        if cats:
            view = view[view["service_category"].isin(cats)]
        st.dataframe(
            view[
                [
                    "borough",
                    "service_category",
                    "service_name",
                    "description",
                    "eligibility",
                    "offered_source",
                    "uptake_evidence",
                    "outcome_evidence",
                    "evidence_source",
                    "families_or_pregnant_specific",
                    "notes",
                ]
            ],
            hide_index=True,
        )

with tab_docs:
    docs = list_policy_documents()
    if docs.empty:
        st.warning(
            "No markdown policy documents yet. Put `.md` files in `policy/national/`, "
            "`policy/newham/` or `policy/comparators/<borough>/`."
        )
    else:
        groups = st.multiselect("Folder", sorted(docs["group"].unique()))
        view = docs[docs["group"].isin(groups)] if groups else docs
        choice = st.selectbox("Document", view["relative_path"])
        path = view.loc[view["relative_path"] == choice, "path"].iloc[0]
        st.caption(f"policy/{choice}")
        st.markdown(path.read_text(encoding="utf-8"))

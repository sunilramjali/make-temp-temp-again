import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import viz
from components import chart_title, page_header, read_doc, table_view
from ta_london.paths import SERVICES_MAP
from ta_london.services import add_evidence_states, list_policy_documents, load_services

st.set_page_config(page_title="Policies and services · TA in London", layout="wide")
page_header(
    "Policies and services",
    "What each borough offers, kept separate from evidence that a service is used or works. "
    "A published scheme is not evidence that it works.",
)

CATEGORY_LABELS = {
    "prevention": "Prevention",
    "prs_access": "Private rented access",
    "landlord_incentives": "Landlord incentives",
    "deposits": "Deposits",
    "allocations": "Allocations",
    "tenancy_support": "Tenancy support",
}
STATES = ["Not recorded", "Offered", "Offered, uptake evidence", "Offered, outcome evidence"]

services = add_evidence_states(load_services()) if SERVICES_MAP.exists() else pd.DataFrame()

tab_overview, tab_table, tab_docs, tab_brief, tab_sources = st.tabs(
    ["Overview", "All services", "Policy documents", "Evidence brief", "Source links"]
)

with tab_overview:
    if services.empty:
        st.info(
            "`policy/services_map.csv` has no rows yet. Add one row per borough and service, "
            "citing the policy document and page."
        )
    else:
        c = st.columns(3)
        c[0].metric("Services offered", f"{int(services['offered'].sum())}")
        c[1].metric("With uptake evidence", f"{int(services['has_uptake_evidence'].sum())}")
        c[2].metric("With outcome evidence", f"{int(services['has_outcome_evidence'].sum())}")

        chart_title(
            "Evidence for each service",
            "Offered means a published document describes it. Uptake and outcome need separate "
            "evidence: numbers using it, or results.",
        )
        checklist = pd.DataFrame(
            {
                "Borough": services["borough"],
                "Category": services["service_category"].map(CATEGORY_LABELS),
                "Service": services["service_name"],
                "Offered": services["offered"],
                "Uptake": services["has_uptake_evidence"],
                "Outcome": services["has_outcome_evidence"],
                "Source": services["offered_source"],
            }
        ).sort_values(["Borough", "Category", "Service"])
        st.dataframe(
            checklist,
            hide_index=True,
            width="stretch",
            height=38 + 35 * len(checklist),
            column_config={
                "Borough": st.column_config.TextColumn(width="small"),
                "Offered": st.column_config.CheckboxColumn(width="small"),
                "Uptake": st.column_config.CheckboxColumn(width="small"),
                "Outcome": st.column_config.CheckboxColumn(width="small"),
                "Service": st.column_config.TextColumn(width="large"),
                "Source": st.column_config.TextColumn(width="medium"),
            },
        )

        # Borough x category matrix: highest evidence level recorded in each cell.
        grid = (
            services.pivot_table(
                index="borough", columns="service_category", values="evidence_level", aggfunc="max"
            )
            .reindex(columns=list(CATEGORY_LABELS))
            .fillna(0)
            .astype(int)
        )
        chart_title(
            "Borough by service category",
            "Each cell shows the strongest evidence recorded. Only Newham is mapped so far; "
            "comparator boroughs will appear as rows.",
        )
        ramp = viz.tok("ordinal")
        colours = [viz.tok("neutral"), ramp[0], ramp[1], ramp[2]]
        scale = []
        for i, col in enumerate(colours):
            scale += [[i / 4, col], [(i + 1) / 4, col]]
        short = ["None recorded", "Offered", "Uptake", "Outcome"]
        text_colour = [viz.tok("ink2"), "#0b0b0b", "#ffffff", "#ffffff"]
        x_labels = [CATEGORY_LABELS[c] for c in grid.columns]
        fig = go.Figure(
            go.Heatmap(
                z=grid.values,
                x=x_labels,
                y=list(grid.index),
                zmin=-0.5,
                zmax=3.5,
                colorscale=scale,
                showscale=False,
                xgap=3,
                ygap=3,
                customdata=[[STATES[v] for v in row] for row in grid.values],
                hovertemplate="%{y} · %{x}: %{customdata}<extra></extra>",
            )
        )
        # Cell labels as annotations: white on the dark steps, near-black on the light ones.
        for yi, borough in enumerate(grid.index):
            for xi, label_ in enumerate(x_labels):
                v = int(grid.values[yi][xi])
                fig.add_annotation(
                    x=label_,
                    y=borough,
                    text=short[v],
                    showarrow=False,
                    font={"size": 12, "color": text_colour[v]},
                )
        viz.style(fig, height=max(150, 64 * len(grid) + 70), legend=False)
        fig.update_xaxes(showgrid=False, side="top", showline=False)
        fig.update_yaxes(showgrid=False, showline=False, autorange="reversed")
        st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})
        chips = "".join(
            f'<span class="pill"><span class="swatch" style="background:{c}"></span>{s}</span>'
            for c, s in zip(colours, STATES, strict=True)
        )
        st.markdown(chips, unsafe_allow_html=True)
        table_view(
            grid.rename(columns=CATEGORY_LABELS)
            .map(lambda v: STATES[v])
            .reset_index(names="Borough")
        )

with tab_table:
    if services.empty:
        st.write("No rows yet.")
    else:
        f1, f2 = st.columns(2)
        boroughs = f1.multiselect("Borough", sorted(services["borough"].unique()))
        cats = f2.multiselect(
            "Service category",
            list(CATEGORY_LABELS),
            format_func=CATEGORY_LABELS.get,
        )
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
            ].rename(columns=lambda c: c.replace("_", " ").capitalize()),
            hide_index=True,
            width="stretch",
        )

with tab_docs:
    docs = list_policy_documents()
    if docs.empty:
        st.info(
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

with tab_brief:
    st.markdown(read_doc("docs/newham_evidence_brief.md") or "Evidence brief not found.")

with tab_sources:
    st.markdown(read_doc("docs/source_links.md") or "Source list not found.")

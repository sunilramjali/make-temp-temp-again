"""Tiny hand-made extracts that copy the layout of the real MHCLG/CORE sheets."""

import pandas as pd

from ta_london.ingest import mhclg_ta

NAMES = {
    "E09000001": "City of London",
    "E09000002": "Barking and Dagenham",
    "E09000025": "Newham",
    "E12000007": "London",
    "E92000001": "England",
}


def ta_sheets(newham_value=10.0, city_value="[c]") -> dict[str, pd.DataFrame]:
    """One frame per TA sheet, built from the parser's own column specs."""
    sheets = {}
    for sheet, specs in mhclg_ta.SPECS.items():
        # Some labels appear in two specs (e.g. 'Not known'); the real sheet has one column.
        labels = list(dict.fromkeys(s[0] for s in specs))
        # Real headers carry note references on some columns.
        header = ["Organisation Identification Code", "Area Name"] + [
            f"{lbl} [note 34]" if i == 0 else lbl for i, lbl in enumerate(labels)
        ]
        n = len(labels)
        if sheet == "TA1":
            title = (
                "Table TA1 - Number of households by type as at 31 March 2026, England, [note 1]"
            )
        elif sheet in mhclg_ta.FLOW_SHEETS:
            title = f"Table {sheet} - Number of households, January to March 2026, England"
        else:
            title = f"Table {sheet} - something"
        rows = [
            [title] + [None] * (n + 1),
            ["Return to contents"] + [None] * (n + 1),
            ["This worksheet contains one table."] + [None] * (n + 1),
            ["Some cells refer to notes."] + [None] * (n + 1),
            ["Some shorthand is used."] + [None] * (n + 1),
            header,
            ["E92000001", "ENGLAND"] + [100.0] * n,
            ["E12000007", "London"] + [50.0] * n,
            ["[z]", "Rest of England"] + [50.0] * n,
            ["E12000007", "London"] + [50.0] * n,  # London appears twice in the real tables
            ["\nE07000223", "Adur"] + [1.0] * n,  # not London
            ["E09000025", "Newham"] + [newham_value] * n,
            ["\nE09000001", "City of London"] + [city_value] * n,
            ["E09000002", "Barking & Dagenham"] + [5.0] * n,
        ]
        sheets[sheet] = pd.DataFrame(rows)
    return sheets


def lt600_frames():
    la = pd.DataFrame(
        [
            ["Local Authority Data"] + [None] * 11,
            ["This worksheet contains one table."] + [None] * 11,
            ["This table contains notes."] + [None] * 11,
            [
                "Local authority code",
                "Local authority",
                "LAD24NM",
                "LAD24CD",
                "Region code",
                "Region name",
                "Country",
                "Notes",
                "2011",
                "2018",
                "2019",
                "2022",
            ],
            ["E09000025", "Newham", "Newham", "E09000025", "E12000007", "London", "England", None]
            + [20000, 26139, 27635, 33246],
            ["E09000008", "Croydon", "Croydon", "E09000008", "E12000007", "London", "England", None]
            + [3000, "[x]", 4000, 5470],
            ["E07000223", "Adur", "Adur", "E07000223", "E12000008", "SE", "England", None]
            + [700, 751, 741, 829],
        ]
    )
    imputations = pd.DataFrame(
        [
            ["Imputations made during processing", None, None, None, None],
            ["This worksheet contains one table.", None, None, None, None],
            ["Local authority", "Year", "LAHS variable", "Original value", "Imputed value"],
            ["Croydon", 2022, "cc1a", 0, 5470],
        ]
    )
    return la, imputations

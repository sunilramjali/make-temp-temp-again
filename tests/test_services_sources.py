import pytest

from ta_london.services import REQUIRED_COLUMNS as SERVICE_COLUMNS
from ta_london.services import add_evidence_states, list_policy_documents, load_services
from ta_london.sources import REQUIRED_COLUMNS as SOURCE_COLUMNS
from ta_london.sources import assert_registered, load_sources


def _write(path, columns, rows=()):
    path.write_text(",".join(columns) + "\n" + "".join(",".join(r) + "\n" for r in rows))
    return path


def test_committed_services_map_is_valid():
    df = load_services()  # validates columns and the README category list
    assert not df.empty
    assert (df["offered_source"].str.strip() != "").all(), "every row must cite its source"


def test_services_missing_column_rejected(tmp_path):
    p = _write(tmp_path / "s.csv", SERVICE_COLUMNS[:-1])
    with pytest.raises(ValueError, match="missing columns"):
        load_services(p)


def test_services_unknown_category_rejected(tmp_path):
    row = ["Newham", "deposit", "x"] + [""] * (len(SERVICE_COLUMNS) - 3)
    p = _write(tmp_path / "s.csv", SERVICE_COLUMNS, [row])
    with pytest.raises(ValueError, match="Unknown service_category"):
        load_services(p, allowed_categories=["prevention"])


def test_evidence_states_are_separate(tmp_path):
    cols = SERVICE_COLUMNS
    row = dict.fromkeys(cols, "")
    row.update(borough="Newham", service_category="deposits", offered_source="doc.md")
    p = _write(tmp_path / "s.csv", cols, [[row[c] for c in cols]])
    out = add_evidence_states(load_services(p))
    assert out.loc[0, "offered"]
    assert not out.loc[0, "has_uptake_evidence"]
    assert not out.loc[0, "has_outcome_evidence"]


def test_sources_duplicate_rejected(tmp_path):
    row = ["a"] + [""] * (len(SOURCE_COLUMNS) - 1)
    p = _write(tmp_path / "src.csv", SOURCE_COLUMNS, [row, row])
    with pytest.raises(ValueError, match="Duplicate"):
        load_sources(p)


def test_assert_registered(tmp_path):
    row = ["a"] + [""] * (len(SOURCE_COLUMNS) - 1)
    p = _write(tmp_path / "src.csv", SOURCE_COLUMNS, [row])
    assert_registered(["a"], p)
    with pytest.raises(ValueError, match="not registered"):
        assert_registered(["b"], p)


def test_list_policy_documents(tmp_path):
    (tmp_path / "newham").mkdir()
    (tmp_path / "comparators" / "hackney").mkdir(parents=True)
    (tmp_path / "README.md").write_text("skip")
    (tmp_path / "newham" / "README.md").write_text("skip")
    (tmp_path / "newham" / "allocations.md").write_text("x")
    (tmp_path / "comparators" / "hackney" / "deposits.md").write_text("x")
    docs = list_policy_documents(tmp_path).set_index("relative_path")
    assert set(docs.index) == {"newham/allocations.md", "comparators/hackney/deposits.md"}
    assert docs.loc["newham/allocations.md", "group"] == "newham"
    assert docs.loc["comparators/hackney/deposits.md", "borough"] == "hackney"

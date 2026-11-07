import pandas as pd
import pytest

from ta_london.pipeline import assert_unique, drop_overlap


def frame(value, source):
    return pd.DataFrame(
        [
            dict(
                area_code="E12000007",
                period="2025",
                period_type="calendar_year_average",
                indicator="ta_households_with_children_avg4q",
                breakdown="all",
                value=value,
                source_id=source,
            )
        ]
    )


def test_overlap_within_rounding_keeps_primary_only():
    out = drop_overlap(frame(49648, "t87"), frame(49650, "t88"), tolerance=10)
    assert out.empty


def test_overlap_beyond_rounding_fails():
    with pytest.raises(ValueError, match="disagree"):
        drop_overlap(frame(49648, "t87"), frame(50000, "t88"), tolerance=10)


def test_duplicate_measures_fail():
    with pytest.raises(ValueError, match="Duplicate"):
        assert_unique(pd.concat([frame(1, "a"), frame(2, "b")]))

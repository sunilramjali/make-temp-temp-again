import pandas as pd
import pandera.pandas as pa
import pytest

from ta_london.schema import COLUMNS, validate


def _good_row(**overrides):
    row = {
        "area_code": "E09000025",
        "area_name": "Newham",
        "period": "2024-Q2",
        "period_type": "quarter_end",
        "period_end": pd.Timestamp("2024-06-30"),
        "indicator": "ta_households_total",
        "breakdown": "all",
        "value": 6123.0,
        "value_status": "ok",
        "unit": "households",
        "source_id": "test_source",
    }
    row.update(overrides)
    return row


def _df(*rows):
    return pd.DataFrame(list(rows), columns=COLUMNS)


def test_good_frame_passes():
    validate(_df(_good_row()))


def test_suppressed_value_is_nan_with_status():
    validate(_df(_good_row(value=float("nan"), value_status="suppressed")))


@pytest.mark.parametrize(
    "bad",
    [
        {"area_code": "Newham"},
        {"period_type": "weekly"},
        {"value_status": "unknown"},
        {"indicator": "TA Households"},
        # NaN without a reason, and a zero standing in for suppressed data's status
        {"value": float("nan"), "value_status": "ok"},
        {"value": 0.0, "value_status": "suppressed"},
    ],
)
def test_bad_frames_are_rejected(bad):
    with pytest.raises(pa.errors.SchemaErrors):
        validate(_df(_good_row(**bad)))

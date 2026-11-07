"""Every page must load without exceptions in its empty state (no data, no policies)."""

import pytest
from streamlit.testing.v1 import AppTest

from ta_london.paths import ROOT

PAGES = ["Home.py"] + [f"pages/{p.name}" for p in sorted((ROOT / "app" / "pages").glob("*.py"))]


@pytest.mark.parametrize("page", PAGES)
def test_page_loads(page):
    at = AppTest.from_file(str(ROOT / "app" / page), default_timeout=30).run()
    assert not at.exception

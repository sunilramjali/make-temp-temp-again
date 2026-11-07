from ta_london import paths


def test_root_is_repo_root():
    assert (paths.ROOT / "pyproject.toml").exists()


def test_data_folders_live_under_data():
    for p in (paths.RAW, paths.INTERIM, paths.PROCESSED, paths.REFERENCE):
        assert p.parent == paths.DATA


def test_services_map_is_in_policy():
    assert paths.SERVICES_MAP.parent == paths.POLICY

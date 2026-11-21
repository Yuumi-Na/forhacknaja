from mordin.vision.stub import read_lab_sheet_stub


def test_default_fixture_for_unknown_name():
    r = read_lab_sheet_stub("photo123.jpg")
    assert r.ph == 5.7 and r.sheet_recommendations[0].fertilizer == "urea"


def test_default_fixture_for_missing_name():
    assert read_lab_sheet_stub(None) == read_lab_sheet_stub("whatever.png")


def test_stem_selects_fixture():
    assert read_lab_sheet_stub("demo_not_dld.jpg").reason_code == "not_dld_sheet"
    assert read_lab_sheet_stub("demo_sheet_acidic.png").ph < 6.0


def test_path_traversal_falls_back_to_default():
    assert read_lab_sheet_stub("../../data/limits.json") == read_lab_sheet_stub("x.jpg")
    assert read_lab_sheet_stub("manual_ph_only.jpg") == read_lab_sheet_stub("x.jpg")


def test_fixtures_dir_override(tmp_path):
    (tmp_path / "demo_sheet_ok.json").write_text('{"ph": 6.1}', encoding="utf-8")
    assert read_lab_sheet_stub("a.jpg", fixtures=tmp_path).ph == 6.1

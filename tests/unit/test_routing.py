from mordin.fertilizer.routing import NeedMoreValues, choose_path

REQUIRED = ["om", "p", "k", "ca", "mg"]
FULL = {"om": 2.0, "p": 10, "k": 80, "ca": 500, "mg": 90}


def test_lab_sheet_with_recommendations_goes_to_sheet():
    recs = [{"fertilizer": "15-15-15", "rate_kg_per_rai": 50}]
    assert choose_path("lab_sheet", {}, recs, REQUIRED) == "sheet"


def test_lab_sheet_without_recommendations_needs_more():
    result = choose_path("lab_sheet", FULL, [], REQUIRED)
    assert isinstance(result, NeedMoreValues)


def test_full_values_without_ph_goes_to_basic_formula():
    assert choose_path("manual", FULL, [], REQUIRED) == "basic_formula"


def test_full_values_with_ph_goes_to_basic_formula():
    assert choose_path("manual", {**FULL, "ph": 5.5}, [], REQUIRED) == "basic_formula"


def test_ph_only_goes_to_ph_only():
    values = {"ph": 5.2, "om": None, "p": None}
    assert choose_path("manual", values, [], REQUIRED) == "ph_only"


def test_some_values_lists_missing_required_fields():
    result = choose_path("manual", {"om": 2.0, "p": 10, "ph": 5.5}, [], REQUIRED)
    assert result == NeedMoreValues(("k", "ca", "mg"))


def test_no_values_needs_all_required_fields():
    result = choose_path("manual", {}, [], REQUIRED)
    assert result == NeedMoreValues(tuple(REQUIRED))

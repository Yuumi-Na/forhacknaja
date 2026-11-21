from decimal import Decimal as D

from mordin.explain import messages
from mordin.explain.table import PARTIAL_NOTE, build_table
from mordin.fertilizer.plan import Plan, PlanItem


def _item(key, rate, total, price):
    return PlanItem(key, D(rate), D(total), None if price is None else D(price), int(D(total)), D("2"))


def _plan(items, area="5"):
    return Plan("sheet", D(area), tuple(items), "2025-01-01", False)


def test_table_shape_and_figures():
    t = build_table(_plan([_item("urea", "20.98", "104.9", "2098"), _item("dap", "10", "50.0", "1000")]))
    assert "5" in t.heading and len(t.columns) == 5
    assert len(t.rows) == 2 and all(len(r) == 5 for r in t.rows)
    assert t.rows[0][1] == "20.98" and t.rows[0][2] == "104.9"
    assert t.rows[0][3] == "2098 บาท"
    assert t.rows[0][4] == messages.item_description("urea")
    assert t.total_row[3] == "3098 บาท"
    assert PARTIAL_NOTE not in t.total_row[3]
    assert "104.9" in t.text_version and "3098" in t.text_version
    assert messages.ESTIMATED_LABEL in t.columns[3]


def test_unpriced_row_shows_no_price_and_total_notes_it():
    t = build_table(_plan([_item("urea", "20", "100.0", "2000"), _item("15-15-15", "30", "150.0", None)]))
    assert t.rows[1][3] == messages.NO_PRICE
    assert t.total_row[3] == f"2000 บาท ({PARTIAL_NOTE})"
    assert messages.NO_PRICE in t.text_version


def test_no_priced_items_total():
    t = build_table(_plan([_item("15-15-15", "30", "150.0", None)]))
    assert t.total_row[3].startswith(messages.NO_PRICE)
    assert PARTIAL_NOTE in t.total_row[3]

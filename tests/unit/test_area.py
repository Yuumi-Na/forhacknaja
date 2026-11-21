from decimal import Decimal

import pytest

from mordin.fertilizer.area import AreaError, parse_area
from mordin.fertilizer.rounding import round_half_up


@pytest.mark.parametrize(
    "text,expected",
    [
        ("5", 5.0),
        ("5 ไร่", 5.0),
        ("3 ไร่ 2 งาน", 3.5),
        ("3 ไร่ 2 งาน 50 ตารางวา", 3.625),
        ("1 เฮกตาร์", 6.25),
        ("1600 ตร.ม.", 1.0),
        ("1600 m2", 1.0),
        ("200 ตร.ว.", 0.5),
        ("๓ ไร่", 3.0),
        ("1 ตารางเมตร", 0.0006),
    ],
)
def test_parse_area_accepts(text, expected):
    assert parse_area(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "   ", "0", "0 ไร่", "-3", "-3 ไร่", "abc", "ไร่", "3 ไร่ 2 ไร่",
     "3 ไร่ 2", "5 ฟุต", "3 ไร่ x"],
)
def test_parse_area_rejects(text):
    with pytest.raises(AreaError):
        parse_area(text)


def test_round_half_up():
    assert round_half_up("0.05", 1) == Decimal("0.1")
    assert round_half_up(2.5) == Decimal("3")
    assert round_half_up("104.94", 1) == Decimal("104.9")

import math

import pytest

from src.processing.clean_data import (
    clean_percentage,
    clean_seconds,
    clean_text_nuclear,
    split_stats,
)


def _assert_equal_or_nan(actual, expected):
    if isinstance(expected, float) and math.isnan(expected):
        assert isinstance(actual, float) and math.isnan(actual)
    else:
        assert actual == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Herb Dean \n \n   ", "Herb Dean"),
        ("SUB \n Rear Naked Choke", "SUB Rear Naked Choke"),
        ("  A   B   C  ", "A B C"),
        (None, ""),
    ],
)
def test_clean_text_nuclear(raw, expected):
    assert clean_text_nuclear(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("4:31", 271),
        ("0:59", 59),
        ("120", 120),
        ("--", math.nan),
        ("---", math.nan),
        (None, math.nan),
        ("invalid", math.nan),
    ],
)
def test_clean_seconds(raw, expected):
    _assert_equal_or_nan(clean_seconds(raw), expected)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("31 of 55", (31, 55)),
        ("0 of 1", (0, 1)),
        ("---", (math.nan, math.nan)),
        ("--", (math.nan, math.nan)),
        (None, (math.nan, math.nan)),
        ("31/55", (math.nan, math.nan)),
        ("bad of value", (math.nan, math.nan)),
    ],
)
def test_split_stats(raw, expected):
    landed, attempted = split_stats(raw)
    _assert_equal_or_nan(landed, expected[0])
    _assert_equal_or_nan(attempted, expected[1])


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("55%", 0.55),
        ("0%", 0.0),
        ("100%", 1.0),
        ("--", math.nan),
        (None, math.nan),
        ("abc%", math.nan),
    ],
)
def test_clean_percentage(raw, expected):
    _assert_equal_or_nan(clean_percentage(raw), expected)

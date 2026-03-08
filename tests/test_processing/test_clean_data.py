import pytest

from src.processing.clean_data import (
    clean_percentage,
    clean_seconds,
    clean_text_nuclear,
    split_stats,
)


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
        ("--", 0),
        ("---", 0),
        (None, 0),
        ("invalid", 0),
    ],
)
def test_clean_seconds(raw, expected):
    assert clean_seconds(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("31 of 55", (31, 55)),
        ("0 of 1", (0, 1)),
        ("---", (0, 0)),
        ("--", (0, 0)),
        (None, (0, 0)),
        ("31/55", (0, 0)),
        ("bad of value", (0, 0)),
    ],
)
def test_split_stats(raw, expected):
    assert split_stats(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("55%", 0.55),
        ("0%", 0.0),
        ("100%", 1.0),
        ("--", 0.0),
        (None, 0.0),
        ("abc%", 0.0),
    ],
)
def test_clean_percentage(raw, expected):
    assert clean_percentage(raw) == expected
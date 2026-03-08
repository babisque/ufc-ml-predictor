import numpy as np
import pandas as pd
import pytest

from src.processing.clean_fighters import (
    clean_height,
    clean_name,
    clean_reach,
    clean_weight,
    parse_dob,
)


def test_clean_name_removes_record_and_whitespace():
    raw = "Colby Covington \n Record: 17-3"
    assert clean_name(raw) == "Colby Covington"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5' 10\"", pytest.approx(177.8, rel=1e-3)),
        ("6' 0\"", pytest.approx(182.88, rel=1e-3)),
        ("--", np.nan),
        (None, np.nan),
    ],
)
def test_clean_height(raw, expected):
    result = clean_height(raw)
    if isinstance(expected, float) and np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("155 lbs.", pytest.approx(70.30676, rel=1e-5)),
        ("205 lbs.", pytest.approx(92.98636, rel=1e-5)),
        ("--", np.nan),
        (None, np.nan),
    ],
)
def test_clean_weight(raw, expected):
    result = clean_weight(raw)
    if isinstance(expected, float) and np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('70\"', pytest.approx(177.8, rel=1e-3)),
        ('72\"', pytest.approx(182.88, rel=1e-3)),
        ("--", np.nan),
        (None, np.nan),
    ],
)
def test_clean_reach(raw, expected):
    result = clean_reach(raw)
    if isinstance(expected, float) and np.isnan(expected):
        assert np.isnan(result)
    else:
        assert result == expected


def test_parse_dob_valid():
    result = parse_dob("Jul 21, 1991")
    assert pd.notna(result)
    assert result.year == 1991 and result.month == 7 and result.day == 21


@pytest.mark.parametrize("raw", ["--", None, "invalid date"])
def test_parse_dob_invalid(raw):
    result = parse_dob(raw)
    assert pd.isna(result)
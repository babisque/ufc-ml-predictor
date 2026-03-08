import numpy as np
import pandas as pd
import pytest

from src.processing.merge_data import calculate_age


def test_calculate_age_valid():
    row = pd.Series({"dob": "1990-01-01", "event_date": "2020-01-01"})
    age = calculate_age(row, "dob", "event_date")
    assert age == pytest.approx(30.0, rel=0.01)


def test_calculate_age_missing_values():
    row = pd.Series({"dob": None, "event_date": "2020-01-01"})
    age = calculate_age(row, "dob", "event_date")
    assert np.isnan(age)


def test_calculate_age_invalid_values():
    row = pd.Series({"dob": "bad-date", "event_date": "2020-01-01"})
    age = calculate_age(row, "dob", "event_date")
    assert np.isnan(age)
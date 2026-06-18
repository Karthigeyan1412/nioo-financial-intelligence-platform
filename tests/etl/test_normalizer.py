import pytest

from src.etl.loader import (
    normalize_year,
    normalize_ticker
)


# ======================================
# 20 YEAR TEST CASES
# ======================================

@pytest.mark.parametrize(
    "input_year,expected",
    [
        ("2024", 2024),
        ("2023", 2023),
        ("2022", 2022),
        (2024, 2024),
        (2023, 2023),
        (2024.0, 2024),
        (2023.0, 2023),
        ("FY2024", 2024),
        ("FY2023", 2023),
        ("FY2022", 2022),
        ("2024-25", 2024),
        ("2023-24", 2023),
        ("Year2024", 2024),
        ("Year2023", 2023),
        (" 2024 ", 2024),
        ("   2023   ", 2023),
        ("Financial Year 2024", 2024),
        ("Financial Year 2023", 2023),
        (None, None),
        ("ABC", None),
    ]
)
def test_normalize_year(input_year, expected):
    assert normalize_year(input_year) == expected


# ======================================
# 20 TICKER TEST CASES
# ======================================

@pytest.mark.parametrize(
    "input_ticker,expected",
    [
        ("tcs", "TCS"),
        ("TCS", "TCS"),
        (" tcs ", "TCS"),
        ("tcs.ns", "TCS"),
        ("TCS.NS", "TCS"),
        ("infy", "INFY"),
        ("INFY", "INFY"),
        ("infy.ns", "INFY"),
        ("reliance", "RELIANCE"),
        ("reliance.ns", "RELIANCE"),
        ("sbin", "SBIN"),
        ("sbin.ns", "SBIN"),
        ("hdfcbank", "HDFCBANK"),
        ("hdfcbank.ns", "HDFCBANK"),
        ("icicibank", "ICICIBANK"),
        ("icicibank.ns", "ICICIBANK"),
        ("bajajfinance", "BAJAJFINANCE"),
        ("bajajfinance.ns", "BAJAJFINANCE"),
        ("ultracemco", "ULTRACEMCO"),
        (None, None),
    ]
)
def test_normalize_ticker(input_ticker, expected):
    assert normalize_ticker(input_ticker) == expected

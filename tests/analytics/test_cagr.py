import pytest

from src.analytics.cagr import (
    BOTH_NEGATIVE,
    DECLINE_TO_LOSS,
    INSUFFICIENT,
    INVALID_INPUT,
    OK,
    TURNAROUND,
    ZERO_BASE,
    calculate_cagr,
    calculate_metric_cagrs,
    calculate_profitandloss_cagrs,
)


def test_calculate_cagr_normal_case():
    result = calculate_cagr(100, 121, 2)

    assert result.flag == OK
    assert result.value == pytest.approx(10)


def test_revenue_cagr_is_stored_with_flag():
    records = [
        {"year": 2020, "sales": 100},
        {"year": 2023, "sales": 133.1},
    ]

    result = calculate_metric_cagrs(records, "sales", "revenue", periods=(3,))

    assert result["revenue_cagr_3yr"] == pytest.approx(10, rel=0.01)
    assert result["revenue_cagr_3yr_flag"] == OK


def test_pat_cagr_is_stored_with_flag():
    records = [
        {"year": 2020, "net_profit": 100},
        {"year": 2025, "net_profit": 161.051},
    ]

    result = calculate_metric_cagrs(records, "net_profit", "pat", periods=(5,))

    assert result["pat_cagr_5yr"] == pytest.approx(10, rel=0.01)
    assert result["pat_cagr_5yr_flag"] == OK


def test_eps_cagr_is_stored_with_flag():
    records = [
        {"year": 2013, "eps": 100},
        {"year": 2023, "eps": 259.374},
    ]

    result = calculate_metric_cagrs(records, "eps", "eps", periods=(10,))

    assert result["eps_cagr_10yr"] == pytest.approx(10, rel=0.01)
    assert result["eps_cagr_10yr_flag"] == OK


def test_turnaround_returns_none_with_flag():
    result = calculate_cagr(-100, 50, 3)

    assert result.value is None
    assert result.flag == TURNAROUND


def test_decline_to_loss_returns_none_with_flag():
    result = calculate_cagr(100, -50, 3)

    assert result.value is None
    assert result.flag == DECLINE_TO_LOSS


def test_both_negative_returns_none_with_flag():
    result = calculate_cagr(-100, -50, 3)

    assert result.value is None
    assert result.flag == BOTH_NEGATIVE


def test_zero_base_returns_none_with_flag():
    result = calculate_cagr(0, 100, 3)

    assert result.value is None
    assert result.flag == ZERO_BASE


def test_insufficient_data_returns_none_with_flag():
    records = [
        {"year": 2022, "sales": 100},
        {"year": 2023, "sales": 120},
    ]

    result = calculate_metric_cagrs(records, "sales", "revenue", periods=(3,))

    assert result["revenue_cagr_3yr"] is None
    assert result["revenue_cagr_3yr_flag"] == INSUFFICIENT


def test_invalid_missing_input_returns_none_with_flag():
    result = calculate_cagr(None, 100, 3)

    assert result.value is None
    assert result.flag == INVALID_INPUT


def test_profitandloss_cagrs_include_revenue_pat_and_eps_flags():
    records = [
        {"year": 2020, "sales": 100, "net_profit": 100, "eps": 100},
        {"year": 2023, "sales": 133.1, "net_profit": -10, "eps": 0},
    ]

    result = calculate_profitandloss_cagrs(records)

    assert result["revenue_cagr_3yr_flag"] == OK
    assert result["pat_cagr_3yr_flag"] == DECLINE_TO_LOSS
    assert result["eps_cagr_3yr_flag"] == OK

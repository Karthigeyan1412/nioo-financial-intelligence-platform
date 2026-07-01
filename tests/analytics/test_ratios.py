import logging

import pytest

from src.analytics.ratios import (
    calculate_asset_turnover,
    calculate_debt_to_equity,
    calculate_interest_coverage_ratio,
    calculate_leverage_efficiency_metrics,
    calculate_net_debt,
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_assets,
    calculate_return_on_capital_employed,
    calculate_return_on_equity,
    get_icr_label,
    has_icr_warning,
    is_high_leverage,
    is_roce_above_threshold,
)


def test_net_profit_margin_normal_calculation():
    assert calculate_net_profit_margin(net_profit=25, sales=100) == 25


def test_net_profit_margin_returns_none_when_sales_zero():
    assert calculate_net_profit_margin(net_profit=25, sales=0) is None


def test_operating_profit_margin_logs_warning_for_mismatch(caplog):
    with caplog.at_level(logging.WARNING):
        result = calculate_operating_profit_margin(
            operating_profit=30,
            sales=100,
            reported_opm_percentage=20,
            company_id="TCS",
        )

    assert result == 30
    assert "Operating profit margin mismatch for TCS" in caplog.text


def test_return_on_equity_normal_calculation():
    assert calculate_return_on_equity(
        net_profit=20,
        equity_capital=25,
        reserves=75,
    ) == 20


def test_return_on_equity_returns_none_for_negative_equity():
    assert calculate_return_on_equity(
        net_profit=20,
        equity_capital=25,
        reserves=-30,
    ) is None


def test_return_on_capital_employed_normal_calculation():
    assert calculate_return_on_capital_employed(
        ebit=30,
        equity_capital=50,
        reserves=50,
        borrowings=50,
    ) == 20


def test_financial_sector_roce_uses_sector_relative_benchmark():
    assert is_roce_above_threshold(
        roce=12,
        broad_sector="Financials",
        normal_threshold=15,
        financial_sector_benchmark=10,
    )


def test_return_on_assets_normal_calculation():
    assert calculate_return_on_assets(net_profit=12, total_assets=200) == 6


def test_return_on_assets_returns_none_when_assets_zero():
    assert calculate_return_on_assets(net_profit=12, total_assets=0) is None


def test_debt_free_company_returns_debt_to_equity_zero():
    assert calculate_debt_to_equity(
        borrowings=0,
        equity_capital=10,
        reserves=90,
    ) == 0


def test_debt_to_equity_normal_calculation():
    assert calculate_debt_to_equity(
        borrowings=50,
        equity_capital=25,
        reserves=75,
    ) == 0.5


def test_interest_zero_returns_icr_none_and_debt_free_label():
    icr = calculate_interest_coverage_ratio(
        operating_profit=100,
        other_income=10,
        interest=0,
    )

    assert icr is None
    assert get_icr_label(icr, interest=0) == "Debt Free"


def test_interest_coverage_ratio_normal_calculation():
    assert calculate_interest_coverage_ratio(
        operating_profit=100,
        other_income=20,
        interest=10,
    ) == 12


def test_high_leverage_flag_ignores_financial_sector():
    assert is_high_leverage(debt_to_equity=6, broad_sector="Industrials")
    assert not is_high_leverage(debt_to_equity=6, broad_sector="Financials")


def test_icr_warning_flag_when_icr_below_threshold():
    assert has_icr_warning(1.2)
    assert not has_icr_warning(1.5)


def test_net_debt_calculation():
    assert calculate_net_debt(borrowings=100, investments=40) == 60


def test_asset_turnover_calculation():
    assert calculate_asset_turnover(sales=250, total_assets=500) == 0.5


def test_asset_turnover_returns_none_when_assets_zero():
    assert calculate_asset_turnover(sales=250, total_assets=0) is None


def test_leverage_efficiency_metrics_combines_day09_outputs():
    metrics = calculate_leverage_efficiency_metrics(
        sales=200,
        operating_profit=20,
        other_income=5,
        interest=20,
        borrowings=600,
        investments=100,
        equity_capital=50,
        reserves=50,
        total_assets=400,
        broad_sector="Industrials",
    )

    assert metrics == {
        "debt_to_equity": 6,
        "high_leverage_flag": True,
        "interest_coverage_ratio": 1.25,
        "icr_label": None,
        "icr_warning_flag": True,
        "net_debt": 500,
        "asset_turnover": 0.5,
    }


@pytest.mark.parametrize(
    "value",
    [None, 0],
)
def test_interest_zero_like_values_are_debt_free(value):
    icr = calculate_interest_coverage_ratio(10, 5, value)

    assert icr is None
    assert get_icr_label(icr, value) == "Debt Free"

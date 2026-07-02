import pandas as pd

from src.analytics.cashflow import (
    calculate_capex_intensity,
    calculate_cfo_quality_score,
    calculate_fcf_conversion_rate,
    calculate_free_cash_flow,
    classify_capex_intensity,
    classify_capital_allocation_pattern,
    classify_cfo_quality,
    generate_capital_allocation_report,
)


def test_free_cash_flow_calculation():
    assert calculate_free_cash_flow(operating_activity=100, investing_activity=-40) == 60


def test_negative_free_cash_flow_is_valid():
    assert calculate_free_cash_flow(operating_activity=50, investing_activity=-90) == -40


def test_cfo_quality_classifications():
    assert classify_cfo_quality(1.2) == "High Quality"
    assert classify_cfo_quality(0.75) == "Moderate"
    assert classify_cfo_quality(0.4) == "Accrual Risk"


def test_cfo_quality_score_returns_none_when_pat_zero():
    assert calculate_cfo_quality_score([(100, 0)]) is None


def test_cfo_quality_score_averages_latest_five_pairs():
    pairs = [(120, 100), (90, 100), (100, 100), (80, 100), (110, 100), (999, 1)]

    assert calculate_cfo_quality_score(pairs) == 1.0


def test_capex_intensity_classifications():
    assert classify_capex_intensity(calculate_capex_intensity(-2, 100)) == "Asset Light"
    assert classify_capex_intensity(calculate_capex_intensity(-5, 100)) == "Moderate"
    assert classify_capex_intensity(calculate_capex_intensity(-10, 100)) == "Capital Intensive"


def test_capex_intensity_returns_none_when_sales_zero():
    assert calculate_capex_intensity(investing_activity=-10, sales=0) is None


def test_fcf_conversion_rate_calculation():
    assert calculate_fcf_conversion_rate(free_cash_flow=50, operating_profit=100) == 50


def test_fcf_conversion_rate_returns_none_when_operating_profit_zero():
    assert calculate_fcf_conversion_rate(free_cash_flow=50, operating_profit=0) is None


def test_capital_allocation_patterns():
    assert classify_capital_allocation_pattern(10, -5, -2) == "Reinvestor"
    assert classify_capital_allocation_pattern(10, -5, -2, "High Quality") == "Shareholder Returns"
    assert classify_capital_allocation_pattern(10, 5, -2) == "Liquidating Assets"
    assert classify_capital_allocation_pattern(-10, 5, 2) == "Distress Signal"
    assert classify_capital_allocation_pattern(-10, -5, 2) == "Growth Funded by Debt"
    assert classify_capital_allocation_pattern(10, 5, 2) == "Cash Accumulator"
    assert classify_capital_allocation_pattern(-10, -5, -2) == "Pre-Revenue"
    assert classify_capital_allocation_pattern(10, -5, 2) == "Mixed"


def test_capital_allocation_missing_values_are_treated_as_zero_and_mixed():
    assert classify_capital_allocation_pattern(None, None, None) == "Mixed"


def test_generate_capital_allocation_report(tmp_path):
    db_path = tmp_path / "test.db"
    output_path = tmp_path / "capital_allocation.csv"
    cashflow = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "year": [2024],
            "operating_activity": [100],
            "investing_activity": [-50],
            "financing_activity": [-20],
        }
    )
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        cashflow.to_sql("cashflow", connection, index=False)

    generated_path = generate_capital_allocation_report(db_path, output_path)
    result = pd.read_csv(generated_path)

    assert generated_path == output_path
    assert result.to_dict("records") == [
        {
            "company_id": "TCS",
            "year": 2024,
            "cfo_sign": "+",
            "cfi_sign": "-",
            "cff_sign": "-",
            "pattern_label": "Reinvestor",
        }
    ]

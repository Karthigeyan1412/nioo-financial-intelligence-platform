import pandas as pd

from src.analytics.financial_ratios_builder import build_financial_ratios_table


def test_build_financial_ratios_table_populates_requested_kpis(tmp_path):
    tables = _sample_tables()

    result = build_financial_ratios_table(
        tables,
        edge_log_path=tmp_path / "ratio_edge_cases.log",
    )

    latest = result[result["year"].eq(2024)].iloc[0]

    assert len(result) == 6
    assert latest["net_profit_margin_pct"] == 10
    assert latest["operating_profit_margin_pct"] == 20
    assert latest["return_on_equity_pct"] == 10
    assert latest["debt_to_equity"] == 0.25
    assert latest["interest_coverage"] == 5
    assert latest["asset_turnover"] == 2
    assert latest["free_cash_flow_cr"] == 70
    assert latest["capex_cr"] == 30
    assert latest["earnings_per_share"] == 5
    assert latest["book_value_per_share"] == 4
    assert latest["dividend_payout_ratio_pct"] == 30
    assert latest["total_debt_cr"] == 50
    assert latest["cash_from_operations_cr"] == 100
    assert latest["revenue_cagr_5yr"] is not None
    assert latest["pat_cagr_5yr"] is not None
    assert latest["eps_cagr_5yr"] is not None
    assert latest["revenue_cagr_5yr_flag"] == "OK"
    assert latest["pat_cagr_5yr_flag"] == "OK"
    assert latest["eps_cagr_5yr_flag"] == "OK"
    assert latest["composite_quality_score"] is not None


def test_build_financial_ratios_table_logs_roe_roce_discrepancies(tmp_path):
    edge_log_path = tmp_path / "ratio_edge_cases.log"

    build_financial_ratios_table(
        _sample_tables(),
        edge_log_path=edge_log_path,
    )

    content = edge_log_path.read_text(encoding="utf-8")

    assert "FORMULA_DISCREPANCY" in content
    assert "return_on_equity_pct" in content
    assert "return_on_capital_employed_pct" in content


def test_build_financial_ratios_table_preserves_source_value_when_computation_missing(tmp_path):
    tables = _sample_tables()
    tables["profitandloss"].loc[tables["profitandloss"]["year"].eq(2024), "sales"] = 0

    result = build_financial_ratios_table(
        tables,
        edge_log_path=tmp_path / "ratio_edge_cases.log",
    )

    latest = result[result["year"].eq(2024)].iloc[0]

    assert latest["net_profit_margin_pct"] == 999


def _sample_tables():
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    ratios = pd.DataFrame(
        {
            "id": range(1, 7),
            "company_id": ["TCS"] * 6,
            "year": years,
            "net_profit_margin_pct": [999] * 6,
            "operating_profit_margin_pct": [999] * 6,
            "return_on_equity_pct": [999] * 6,
            "debt_to_equity": [999] * 6,
            "interest_coverage": [999] * 6,
            "asset_turnover": [999] * 6,
            "free_cash_flow_cr": [999] * 6,
            "capex_cr": [999] * 6,
            "earnings_per_share": [999] * 6,
            "book_value_per_share": [999] * 6,
            "dividend_payout_ratio_pct": [999] * 6,
            "total_debt_cr": [999] * 6,
            "cash_from_operations_cr": [999] * 6,
        }
    )
    profitandloss = pd.DataFrame(
        {
            "company_id": ["TCS"] * 6,
            "year": years,
            "sales": [100, 120, 140, 160, 180, 200],
            "operating_profit": [20, 24, 28, 32, 36, 40],
            "opm_percentage": [20] * 6,
            "other_income": [10] * 6,
            "interest": [10] * 6,
            "net_profit": [10, 12, 14, 16, 18, 20],
            "eps": [2, 2.4, 2.8, 3.2, 3.6, 5],
            "dividend_payout": [30] * 6,
        }
    )
    balancesheet = pd.DataFrame(
        {
            "company_id": ["TCS"] * 6,
            "year": years,
            "equity_capital": [50] * 6,
            "reserves": [150] * 6,
            "borrowings": [50] * 6,
            "investments": [20] * 6,
            "total_assets": [100] * 6,
        }
    )
    cashflow = pd.DataFrame(
        {
            "company_id": ["TCS"] * 6,
            "year": years,
            "operating_activity": [100] * 6,
            "investing_activity": [-30] * 6,
            "financing_activity": [-10] * 6,
        }
    )
    companies = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "roe_percentage": [50],
            "roce_percentage": [80],
        }
    )
    sectors = pd.DataFrame(
        {
            "company_id": ["TCS"],
            "broad_sector": ["Information Technology"],
        }
    )

    return {
        "financial_ratios": ratios,
        "profitandloss": profitandloss,
        "balancesheet": balancesheet,
        "cashflow": cashflow,
        "companies": companies,
        "sectors": sectors,
    }

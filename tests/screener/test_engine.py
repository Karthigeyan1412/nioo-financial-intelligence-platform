from pathlib import Path

import pandas as pd

from src.screener.engine import (
    ScreenerEngine,
    add_debt_to_equity_declining,
    latest_company_rows,
    load_screener_dataset,
    run_debt_free_blue_chip,
    run_dividend_champion,
    run_growth_accelerator,
    run_quality_compounder,
    run_turnaround_watch,
    run_value_pick,
)


def test_individual_metric_filtering():
    result = ScreenerEngine().apply_filters(
        _sample_screener_data(),
        {"roe_min": 15},
    )

    assert set(result["company_id"]) == {"AAA", "BBB"}


def test_multiple_filter_combinations():
    result = ScreenerEngine().apply_filters(
        _sample_screener_data(),
        {
            "roe_min": 15,
            "free_cash_flow_min": 0,
            "revenue_cagr_5yr_min": 10,
        },
    )

    assert result["company_id"].tolist() == ["AAA"]


def test_debt_to_equity_filter_exempts_financials():
    result = ScreenerEngine().apply_filters(
        _sample_screener_data(),
        {"debt_to_equity_max": 1},
    )

    assert "BBB" in set(result["company_id"])
    assert "CCC" not in set(result["company_id"])


def test_debt_free_icr_satisfies_minimum_filter():
    result = ScreenerEngine().apply_filters(
        _sample_screener_data(),
        {"interest_coverage_min": 100},
    )

    assert set(result["company_id"]) == {"DDD"}


def test_results_are_sorted_by_composite_quality_score_descending():
    result = ScreenerEngine().apply_filters(
        _sample_screener_data(),
        {"free_cash_flow_min": 0},
    )

    assert result["composite_quality_score"].tolist() == sorted(
        result["composite_quality_score"],
        reverse=True,
    )


def test_engine_adds_composite_quality_score_when_missing():
    data = _sample_screener_data().drop(columns=["composite_quality_score"])

    result = ScreenerEngine().apply_filters(data, {"roe_min": 0})

    assert "composite_quality_score" in result.columns


def test_quality_compounder_preset_executes():
    result = run_quality_compounder(_sample_screener_data())

    assert result["company_id"].tolist() == ["AAA"]


def test_value_pick_preset_executes():
    result = run_value_pick(_sample_screener_data())

    assert set(result["company_id"]) == {"AAA", "BBB"}


def test_growth_accelerator_preset_executes():
    result = run_growth_accelerator(_sample_screener_data())

    assert result["company_id"].tolist() == ["AAA"]


def test_dividend_champion_preset_executes():
    result = run_dividend_champion(_sample_screener_data())

    assert result["company_id"].tolist() == ["DDD"]


def test_debt_free_blue_chip_preset_executes():
    result = run_debt_free_blue_chip(_sample_screener_data())

    assert result["company_id"].tolist() == ["DDD"]


def test_turnaround_watch_preset_executes():
    data = add_debt_to_equity_declining(_sample_screener_data())

    result = run_turnaround_watch(data)

    assert result["company_id"].tolist() == ["EEE"]


def test_latest_company_rows_keeps_latest_year_per_company():
    result = latest_company_rows(_sample_screener_data())

    assert len(result) == 5
    assert result[result["company_id"].eq("EEE")]["year"].iloc[0] == 2024


def test_all_presets_execute_on_full_dataset_if_database_exists():
    if not Path("db/nifty100.db").exists():
        return

    data = load_screener_dataset("db/nifty100.db")
    presets = [
        run_quality_compounder,
        run_value_pick,
        run_growth_accelerator,
        run_dividend_champion,
        run_debt_free_blue_chip,
        run_turnaround_watch,
    ]

    for preset in presets:
        result = preset(data)
        assert isinstance(result, pd.DataFrame)
        assert 0 <= len(result) <= data["company_id"].nunique()


def _sample_screener_data():
    return pd.DataFrame(
        [
            {
                "company_id": "AAA",
                "year": 2024,
                "return_on_equity_pct": 20,
                "debt_to_equity": 0.5,
                "free_cash_flow_cr": 100,
                "revenue_cagr_5yr": 16,
                "revenue_cagr_3yr": 15,
                "pat_cagr_5yr": 25,
                "operating_profit_margin_pct": 22,
                "pe_ratio": 15,
                "pb_ratio": 2,
                "dividend_yield_pct": 1.5,
                "dividend_payout_ratio_pct": 50,
                "interest_coverage": 5,
                "market_cap_crore": 10000,
                "net_profit": 1000,
                "eps_cagr_5yr": 11,
                "asset_turnover": 1.2,
                "sales": 6000,
                "broad_sector": "Industrials",
                "composite_quality_score": 90,
            },
            {
                "company_id": "BBB",
                "year": 2024,
                "return_on_equity_pct": 18,
                "debt_to_equity": 8,
                "free_cash_flow_cr": 50,
                "revenue_cagr_5yr": 8,
                "revenue_cagr_3yr": 9,
                "pat_cagr_5yr": 10,
                "operating_profit_margin_pct": 18,
                "pe_ratio": 10,
                "pb_ratio": 1.5,
                "dividend_yield_pct": 2,
                "dividend_payout_ratio_pct": 70,
                "interest_coverage": 3,
                "market_cap_crore": 8000,
                "net_profit": 900,
                "eps_cagr_5yr": 8,
                "asset_turnover": 0.8,
                "sales": 7000,
                "broad_sector": "Financials",
                "composite_quality_score": 80,
            },
            {
                "company_id": "CCC",
                "year": 2024,
                "return_on_equity_pct": 10,
                "debt_to_equity": 6,
                "free_cash_flow_cr": -10,
                "revenue_cagr_5yr": 20,
                "revenue_cagr_3yr": 20,
                "pat_cagr_5yr": 30,
                "operating_profit_margin_pct": 15,
                "pe_ratio": 30,
                "pb_ratio": 5,
                "dividend_yield_pct": 0.5,
                "dividend_payout_ratio_pct": 20,
                "interest_coverage": 1,
                "market_cap_crore": 3000,
                "net_profit": 100,
                "eps_cagr_5yr": 20,
                "asset_turnover": 1.5,
                "sales": 1000,
                "broad_sector": "Industrials",
                "composite_quality_score": 50,
            },
            {
                "company_id": "DDD",
                "year": 2024,
                "return_on_equity_pct": 14,
                "debt_to_equity": 0,
                "free_cash_flow_cr": 20,
                "revenue_cagr_5yr": 5,
                "revenue_cagr_3yr": 5,
                "pat_cagr_5yr": 5,
                "operating_profit_margin_pct": 12,
                "pe_ratio": 25,
                "pb_ratio": 4,
                "dividend_yield_pct": 3,
                "dividend_payout_ratio_pct": 60,
                "interest_coverage": None,
                "icr_label": "Debt Free",
                "market_cap_crore": 12000,
                "net_profit": 500,
                "eps_cagr_5yr": 5,
                "asset_turnover": 0.5,
                "sales": 8000,
                "broad_sector": "Industrials",
                "composite_quality_score": 70,
            },
            {
                "company_id": "EEE",
                "year": 2023,
                "return_on_equity_pct": 5,
                "debt_to_equity": 3,
                "free_cash_flow_cr": -5,
                "revenue_cagr_5yr": 5,
                "revenue_cagr_3yr": 5,
                "pat_cagr_5yr": 5,
                "operating_profit_margin_pct": 5,
                "pe_ratio": 40,
                "pb_ratio": 6,
                "dividend_yield_pct": 0,
                "dividend_payout_ratio_pct": 0,
                "interest_coverage": 1,
                "market_cap_crore": 1000,
                "net_profit": 10,
                "eps_cagr_5yr": 5,
                "asset_turnover": 0.2,
                "sales": 500,
                "broad_sector": "Industrials",
                "composite_quality_score": 10,
            },
            {
                "company_id": "EEE",
                "year": 2024,
                "return_on_equity_pct": 8,
                "debt_to_equity": 2,
                "free_cash_flow_cr": 15,
                "revenue_cagr_5yr": 8,
                "revenue_cagr_3yr": 12,
                "pat_cagr_5yr": 8,
                "operating_profit_margin_pct": 8,
                "pe_ratio": 35,
                "pb_ratio": 4,
                "dividend_yield_pct": 0,
                "dividend_payout_ratio_pct": 0,
                "interest_coverage": 2,
                "market_cap_crore": 2000,
                "net_profit": 20,
                "eps_cagr_5yr": 8,
                "asset_turnover": 0.4,
                "sales": 1500,
                "broad_sector": "Industrials",
                "composite_quality_score": 20,
            },
        ]
    )

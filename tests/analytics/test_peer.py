import logging
import sqlite3

import pandas as pd

from src.analytics.peer import compute_peer_percentiles, populate_peer_percentiles


def test_normal_percentile_calculation():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
        metrics=["return_on_equity_pct"],
    )

    year_2024 = result[
        result["year"].eq(2024)
        & result["peer_group_name"].eq("Tech")
        & result["metric"].eq("return_on_equity_pct")
    ]

    assert _percentile_for(year_2024, "AAA") == 0
    assert _percentile_for(year_2024, "BBB") == 1


def test_multiple_peer_groups_are_ranked_independently():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
        metrics=["return_on_equity_pct"],
    )

    finance = result[
        result["peer_group_name"].eq("Finance")
        & result["year"].eq(2024)
        & result["metric"].eq("return_on_equity_pct")
    ]

    assert set(finance["company_id"]) == {"CCC", "DDD"}
    assert _percentile_for(finance, "CCC") == 1
    assert _percentile_for(finance, "DDD") == 0


def test_multiple_years_are_ranked_separately():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
        metrics=["return_on_equity_pct"],
    )

    tech_2023 = result[
        result["peer_group_name"].eq("Tech")
        & result["year"].eq(2023)
        & result["metric"].eq("return_on_equity_pct")
    ]
    tech_2024 = result[
        result["peer_group_name"].eq("Tech")
        & result["year"].eq(2024)
        & result["metric"].eq("return_on_equity_pct")
    ]

    assert len(tech_2023) == 2
    assert len(tech_2024) == 2


def test_single_company_peer_group_gets_zero_percent_rank():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
        metrics=["return_on_equity_pct"],
    )

    single = result[
        result["peer_group_name"].eq("Solo")
        & result["metric"].eq("return_on_equity_pct")
    ]

    assert single["percentile_rank"].tolist() == [0]


def test_debt_to_equity_uses_inverse_percentile():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
        metrics=["debt_to_equity"],
    )

    tech = result[
        result["peer_group_name"].eq("Tech")
        & result["year"].eq(2024)
        & result["metric"].eq("debt_to_equity")
    ]

    assert _percentile_for(tech, "AAA") == 1
    assert _percentile_for(tech, "BBB") == 0


def test_missing_peer_group_is_logged_and_skipped(caplog):
    with caplog.at_level(logging.WARNING):
        result = compute_peer_percentiles(
            _financial_ratios(),
            _peer_groups().query("company_id != 'NOPE'"),
            metrics=["return_on_equity_pct"],
        )

    assert "No peer group assigned: NOPE" in caplog.text
    assert "NOPE" not in set(result["company_id"])


def test_sqlite_table_population(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as connection:
        _financial_ratios().to_sql("financial_ratios", connection, index=False)
        _peer_groups().to_sql("peer_groups", connection, index=False)

    result = populate_peer_percentiles(db_path)

    with sqlite3.connect(db_path) as connection:
        table_exists = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'peer_percentiles'
            """
        ).fetchone()[0]
        row_count = connection.execute("SELECT COUNT(*) FROM peer_percentiles").fetchone()[0]

    assert table_exists == 1
    assert row_count == len(result)
    assert row_count > 0


def test_percentile_values_remain_between_zero_and_one():
    result = compute_peer_percentiles(
        _financial_ratios(),
        _peer_groups(),
    )

    assert result["percentile_rank"].between(0, 1).all()


def _percentile_for(df, company_id):
    return df[df["company_id"].eq(company_id)]["percentile_rank"].iloc[0]


def _peer_groups():
    return pd.DataFrame(
        {
            "peer_group_name": [
                "Tech",
                "Tech",
                "Finance",
                "Finance",
                "Solo",
                "Missing",
            ],
            "company_id": ["AAA", "BBB", "CCC", "DDD", "EEE", "NOPE"],
        }
    )


def _financial_ratios():
    return pd.DataFrame(
        {
            "company_id": [
                "AAA",
                "BBB",
                "AAA",
                "BBB",
                "CCC",
                "DDD",
                "EEE",
                "NOPE",
            ],
            "year": [2023, 2023, 2024, 2024, 2024, 2024, 2024, 2024],
            "return_on_equity_pct": [10, 20, 12, 24, 30, 15, 9, 99],
            "return_on_capital_employed_pct": [9, 18, 11, 20, 25, 12, 8, 90],
            "net_profit_margin_pct": [5, 8, 6, 9, 12, 7, 4, 50],
            "debt_to_equity": [0.5, 1.5, 0.4, 2.0, 4.0, 1.0, 0.1, 9],
            "free_cash_flow_cr": [10, 20, 11, 22, 30, 5, 1, 100],
            "pat_cagr_5yr": [5, 10, 6, 12, 20, 4, 2, 30],
            "revenue_cagr_5yr": [6, 12, 8, 16, 22, 5, 3, 40],
            "eps_cagr_5yr": [4, 8, 5, 10, 15, 3, 1, 25],
            "interest_coverage": [2, 5, 3, 6, 8, 1, 0.5, 10],
            "asset_turnover": [0.8, 1.2, 0.9, 1.4, 1.8, 0.6, 0.3, 2.0],
        }
    )

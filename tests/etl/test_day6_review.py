import sqlite3

import pandas as pd

from src.etl.day6_review import (
    build_manual_review_report,
    build_year_coverage,
    detect_data_quality_review_issues,
)


def test_build_year_coverage_counts_distinct_profitandloss_years():
    connection = sqlite3.connect(":memory:")
    pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "TCS", "INFY"],
            "year": [2022, 2023, 2023, 2024],
        }
    ).to_sql("profitandloss", connection, index=False)

    coverage = build_year_coverage(connection)

    assert coverage.to_dict("records") == [
        {"company_id": "INFY", "years_available": 1},
        {"company_id": "TCS", "years_available": 2},
    ]


def test_manual_review_marks_missing_data():
    connection = sqlite3.connect(":memory:")
    pd.DataFrame({"company_id": ["TCS"]}).to_sql("companies", connection, index=False)
    for table_name in ["balancesheet", "cashflow", "profitandloss", "financial_ratios"]:
        pd.DataFrame({"company_id": ["TCS"]}).to_sql(table_name, connection, index=False)
    pd.DataFrame({"company_id": []}).to_sql("market_cap", connection, index=False)

    report = build_manual_review_report(connection, sample_size=1, random_seed=1)

    assert report.loc[0, "company_id"] == "TCS"
    assert report.loc[0, "market_cap_rows"] == 0
    assert report.loc[0, "review_status"] == "MISSING_DATA"


def test_detect_data_quality_review_issues_finds_duplicate_years():
    connection = sqlite3.connect(":memory:")
    for table_name in [
        "cashflow",
        "documents",
        "financial_ratios",
        "market_cap",
        "profitandloss",
    ]:
        pd.DataFrame({"company_id": ["TCS"], "year": [2024]}).to_sql(
            table_name,
            connection,
            index=False,
        )
    pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", None],
            "year": [2024, 2024, None],
        }
    ).to_sql("balancesheet", connection, index=False)

    issues = detect_data_quality_review_issues(connection)

    assert "DUPLICATE_YEAR" in set(issues["issue_type"])
    assert "NULL_COMPANY_ID" in set(issues["issue_type"])
    assert "MALFORMED_YEAR" in set(issues["issue_type"])

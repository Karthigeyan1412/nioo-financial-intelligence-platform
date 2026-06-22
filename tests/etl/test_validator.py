import pandas as pd

from src.etl.validator import DataQualityValidator


def test_validator_reports_core_dq_failures():
    tables = {
        "companies": pd.DataFrame(
            {
                "company_id": ["TCS", "TCS", None],
                "ticker": ["TCS", "TCS", None],
                "sector": ["IT", None, "IT"],
            }
        ),
        "market_cap": pd.DataFrame(
            {
                "company_id": ["UNKNOWN"],
                "year": [2024],
                "market_cap": [-10],
            }
        ),
        "stock_prices": pd.DataFrame(
            {
                "company_id": ["TCS"],
                "ticker": ["TCS"],
                "close_price": [-1],
            }
        ),
    }

    failures = DataQualityValidator().validate(tables)

    assert {"DQ001", "DQ002", "DQ003", "DQ004", "DQ007", "DQ010", "DQ011", "DQ013"} <= set(
        failures["rule_id"]
    )

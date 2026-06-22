import pandas as pd

from src.etl.normaliser import normalize_dataframe


def test_normalize_dataframe_standardizes_columns_and_values():
    df = pd.DataFrame(
        {
            " Company ID ": [" tcs ", None],
            "Ticker": ["tcs.ns", "infy.NS"],
            "Year": ["FY2024", "bad"],
            " Company Name ": [" Tata Consultancy Services ", ""],
        }
    )

    result = normalize_dataframe(df)

    assert list(result.columns) == ["company_id", "ticker", "year", "company_name"]
    assert result.loc[0, "company_id"] == "TCS"
    assert result.loc[0, "ticker"] == "TCS"
    assert result.loc[0, "year"] == 2024
    assert pd.isna(result.loc[1, "year"])
    assert result.loc[0, "company_name"] == "Tata Consultancy Services"

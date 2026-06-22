from datetime import date
from pathlib import Path

import pandas as pd


CURRENT_YEAR = date.today().year


REQUIRED_COLUMNS = {
    "analysis": {"company_id"},
    "companies": {"company_id"},
    "documents": {"company_id"},
    "financial_ratios": {"company_id"},
    "market_cap": {"company_id"},
    "stock_prices": {"company_id"},
    "sectors": {"company_id"},
    "peer_groups": {"company_id"},
    "balancesheet": {"company_id"},
    "cashflow": {"company_id"},
    "profitandloss": {"company_id"},
    "prosandcons": {"company_id"},
}


class DataQualityValidator:
    def validate(self, tables):
        failures = []

        companies = tables.get("companies", pd.DataFrame())
        known_company_ids = _known_values(companies, "company_id")
        known_tickers = _known_values(companies, "ticker")

        for table_name, df in tables.items():
            failures.extend(self._dq001_company_id_not_null(table_name, df))
            failures.extend(self._dq002_ticker_not_null(table_name, df))
            failures.extend(self._dq005_year_integer(table_name, df))
            failures.extend(self._dq006_year_range(table_name, df))
            failures.extend(self._dq009_numeric_values(table_name, df))
            failures.extend(self._dq010_market_cap_non_negative(table_name, df))
            failures.extend(self._dq011_stock_prices_non_negative(table_name, df))
            failures.extend(self._dq012_ratio_numeric(table_name, df))
            failures.extend(self._dq014_no_duplicate_rows(table_name, df))
            failures.extend(self._dq015_required_columns(table_name, df))
            failures.extend(self._dq016_no_empty_rows(table_name, df))

        failures.extend(self._dq003_company_id_unique(companies))
        failures.extend(self._dq004_ticker_unique(companies))
        failures.extend(self._dq007_financial_company_reference(tables, known_company_ids))
        failures.extend(self._dq008_stock_reference(tables, known_company_ids, known_tickers))
        failures.extend(self._dq013_sector_not_null(tables))

        return pd.DataFrame(
            failures,
            columns=["rule_id", "table", "column", "row_id", "value", "message"],
        )

    def write_failures(self, tables, output_path="output/validation_failures.csv"):
        failures = self.validate(tables)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        failures.to_csv(output_path, index=False)
        return output_path

    def _failure(self, rule_id, table, column, row_id, value, message):
        return {
            "rule_id": rule_id,
            "table": table,
            "column": column,
            "row_id": row_id,
            "value": value,
            "message": message,
        }

    def _dq001_company_id_not_null(self, table, df):
        if "company_id" not in df.columns:
            return []
        return [
            self._failure("DQ001", table, "company_id", idx, row["company_id"], "company_id is missing")
            for idx, row in df[df["company_id"].isna()].iterrows()
        ]

    def _dq002_ticker_not_null(self, table, df):
        if "ticker" not in df.columns:
            return []
        return [
            self._failure("DQ002", table, "ticker", idx, row["ticker"], "ticker is missing")
            for idx, row in df[df["ticker"].isna()].iterrows()
        ]

    def _dq003_company_id_unique(self, companies):
        if "company_id" not in companies.columns:
            return []
        duplicated = companies[companies["company_id"].notna() & companies["company_id"].duplicated(keep=False)]
        return [
            self._failure("DQ003", "companies", "company_id", idx, row["company_id"], "company_id must be unique")
            for idx, row in duplicated.iterrows()
        ]

    def _dq004_ticker_unique(self, companies):
        if "ticker" not in companies.columns:
            return []
        duplicated = companies[companies["ticker"].notna() & companies["ticker"].duplicated(keep=False)]
        return [
            self._failure("DQ004", "companies", "ticker", idx, row["ticker"], "ticker must be unique")
            for idx, row in duplicated.iterrows()
        ]

    def _dq005_year_integer(self, table, df):
        if "year" not in df.columns:
            return []
        invalid = df[df["year"].notna() & df["year"].apply(lambda value: not _is_integer_like(value))]
        return [
            self._failure("DQ005", table, "year", idx, row["year"], "year must be an integer")
            for idx, row in invalid.iterrows()
        ]

    def _dq006_year_range(self, table, df):
        if "year" not in df.columns:
            return []
        invalid = df[df["year"].notna() & ~df["year"].between(1990, CURRENT_YEAR)]
        return [
            self._failure("DQ006", table, "year", idx, row["year"], "year must be between 1990 and current year")
            for idx, row in invalid.iterrows()
        ]

    def _dq007_financial_company_reference(self, tables, known_company_ids):
        failures = []
        financial_tables = {"financial_ratios", "market_cap", "balancesheet", "cashflow", "profitandloss"}
        for table in financial_tables:
            df = tables.get(table)
            if df is None or "company_id" not in df.columns:
                continue
            failures.extend(_missing_reference_failures(self, "DQ007", table, df, "company_id", known_company_ids))
        return failures

    def _dq008_stock_reference(self, tables, known_company_ids, known_tickers):
        df = tables.get("stock_prices")
        if df is None:
            return []

        failures = []
        if "company_id" in df.columns:
            failures.extend(_missing_reference_failures(self, "DQ008", "stock_prices", df, "company_id", known_company_ids))
        if "ticker" in df.columns:
            failures.extend(_missing_reference_failures(self, "DQ008", "stock_prices", df, "ticker", known_tickers))
        return failures

    def _dq009_numeric_values(self, table, df):
        failures = []
        ignored = {"ticker", "company_name", "company", "name", "sector", "industry", "peer_group", "pros", "cons", "year", "date"}
        for column in df.columns:
            if _is_text_metadata_column(column, ignored):
                continue
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.notna().sum() == 0:
                continue
            invalid = df[df[column].notna() & numeric.isna()]
            failures.extend(
                self._failure("DQ009", table, column, idx, row[column], f"{column} must be numeric")
                for idx, row in invalid.iterrows()
            )
        return failures

    def _dq010_market_cap_non_negative(self, table, df):
        if table != "market_cap":
            return []
        columns = [column for column in df.columns if "market_cap" in column]
        return _non_negative_failures(self, "DQ010", table, df, columns)

    def _dq011_stock_prices_non_negative(self, table, df):
        if table != "stock_prices":
            return []
        price_columns = [column for column in df.columns if any(key in column for key in ["price", "open", "high", "low", "close"])]
        return _non_negative_failures(self, "DQ011", table, df, price_columns)

    def _dq012_ratio_numeric(self, table, df):
        if table != "financial_ratios":
            return []
        ratio_columns = [column for column in df.columns if column not in {"company_id", "ticker", "year"}]
        failures = []
        for column in ratio_columns:
            if _is_text_metadata_column(column, set()):
                continue
            numeric = pd.to_numeric(df[column], errors="coerce")
            if numeric.notna().sum() == 0:
                continue
            invalid = df[df[column].notna() & numeric.isna()]
            failures.extend(
                self._failure("DQ012", table, column, idx, row[column], f"{column} ratio must be numeric")
                for idx, row in invalid.iterrows()
            )
        return failures

    def _dq013_sector_not_null(self, tables):
        companies = tables.get("companies", pd.DataFrame())
        sectors = tables.get("sectors", pd.DataFrame())
        failures = []

        for table, df in {"companies": companies, "sectors": sectors}.items():
            if "sector" not in df.columns:
                continue
            failures.extend(
                self._failure("DQ013", table, "sector", idx, row["sector"], "sector is missing")
                for idx, row in df[df["sector"].isna()].iterrows()
            )

        return failures

    def _dq014_no_duplicate_rows(self, table, df):
        duplicated = df[df.duplicated(keep=False)]
        return [
            self._failure("DQ014", table, "*", idx, "", "duplicate row found")
            for idx, _ in duplicated.iterrows()
        ]

    def _dq015_required_columns(self, table, df):
        missing = REQUIRED_COLUMNS.get(table, set()) - set(df.columns)
        return [
            self._failure("DQ015", table, column, "", "", f"required column {column} is missing")
            for column in sorted(missing)
        ]

    def _dq016_no_empty_rows(self, table, df):
        empty = df[df.isna().all(axis=1)]
        return [
            self._failure("DQ016", table, "*", idx, "", "empty row found")
            for idx, _ in empty.iterrows()
        ]


def _known_values(df, column):
    if column not in df.columns:
        return set()
    return set(df[column].dropna().astype(str))


def _is_integer_like(value):
    if isinstance(value, int):
        return True

    if isinstance(value, float):
        return value.is_integer()

    return False


def _is_text_metadata_column(column, ignored):
    text_markers = {
        "logo",
        "url",
        "link",
        "website",
        "description",
        "about",
        "business",
        "summary",
        "notes",
        "remarks",
        "source",
    }

    return (
        column in ignored
        or column == "id"
        or column.endswith("_id")
        or any(marker in column for marker in text_markers)
    )


def _missing_reference_failures(validator, rule_id, table, df, column, known_values):
    if not known_values:
        return []

    invalid = df[df[column].notna() & ~df[column].astype(str).isin(known_values)]
    return [
        validator._failure(rule_id, table, column, idx, row[column], f"{column} does not reference companies")
        for idx, row in invalid.iterrows()
    ]


def _non_negative_failures(validator, rule_id, table, df, columns):
    failures = []
    for column in columns:
        if column not in df.columns:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        invalid = df[numeric.notna() & (numeric < 0)]
        failures.extend(
            validator._failure(rule_id, table, column, idx, row[column], f"{column} must be non-negative")
            for idx, row in invalid.iterrows()
        )
    return failures

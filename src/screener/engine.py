from pathlib import Path
import sqlite3

import pandas as pd
import yaml

from src.analytics.cagr import calculate_metric_cagrs


DEFAULT_CONFIG_PATH = "screener_config.yaml"
FINANCIAL_SECTOR = "FINANCIALS"


PRESETS = {
    "quality_compounder": {
        "roe_min": 15,
        "debt_to_equity_max": 1,
        "free_cash_flow_min": 0,
        "revenue_cagr_5yr_min": 10,
    },
    "value_pick": {
        "pe_max": 20,
        "pb_max": 3,
        "debt_to_equity_max": 2,
        "dividend_yield_min": 1,
    },
    "growth_accelerator": {
        "pat_cagr_5yr_min": 20,
        "revenue_cagr_5yr_min": 15,
        "debt_to_equity_max": 2,
    },
    "dividend_champion": {
        "dividend_yield_min": 2,
        "dividend_payout_max": 80,
        "free_cash_flow_min": 0,
    },
    "debt_free_blue_chip": {
        "debt_to_equity_eq": 0,
        "roe_min": 12,
        "sales_min": 5000,
    },
    "turnaround_watch": {
        "revenue_cagr_3yr_min": 10,
        "free_cash_flow_min": 0,
        "debt_to_equity_declining": True,
    },
}


class ScreenerEngine:
    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.config = load_screener_config(self.config_path)

    def apply_filters(self, financial_ratios, filters):
        result = ensure_composite_quality_score(financial_ratios.copy())

        for filter_name, threshold in (filters or {}).items():
            result = self._apply_filter(result, filter_name, threshold)

        return result.sort_values(
            "composite_quality_score",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)

    def run_preset(self, preset_name, financial_ratios):
        return self.apply_filters(financial_ratios, PRESETS[preset_name])

    def _apply_filter(self, df, filter_name, threshold):
        if filter_name == "debt_to_equity_eq":
            return _apply_debt_to_equity_equal(df, threshold)

        if filter_name == "debt_to_equity_declining":
            if not threshold:
                return df
            if "debt_to_equity_declining" not in df.columns:
                df = add_debt_to_equity_declining(df)
            return df[df["debt_to_equity_declining"].fillna(False)]

        metric = self.config["metrics"].get(filter_name)
        if metric is None:
            raise KeyError(f"Unknown screener filter: {filter_name}")

        column = metric["column"]
        operator = metric["operator"]

        if column not in df.columns:
            return df.iloc[0:0]

        if filter_name == "debt_to_equity_max":
            return _apply_debt_to_equity_max(df, column, threshold)

        if filter_name == "interest_coverage_min":
            values = _effective_interest_coverage(df)
        else:
            values = pd.to_numeric(df[column], errors="coerce")

        if operator == "min":
            return df[values > threshold]

        if operator == "max":
            return df[values < threshold]

        raise ValueError(f"Unsupported operator for {filter_name}: {operator}")


def load_screener_config(config_path=DEFAULT_CONFIG_PATH):
    with Path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_screener_dataset(db_path="db/nifty100.db"):
    with sqlite3.connect(db_path) as connection:
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
        market_cap = pd.read_sql_query("SELECT * FROM market_cap", connection)
        profitandloss = pd.read_sql_query("SELECT * FROM profitandloss", connection)
        sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", connection)
        companies = pd.read_sql_query("SELECT company_id, company_name FROM companies", connection)

    dataset = ratios.merge(
        market_cap[
            [
                "company_id",
                "year",
                "market_cap_crore",
                "pe_ratio",
                "pb_ratio",
                "dividend_yield_pct",
            ]
        ],
        on=["company_id", "year"],
        how="left",
    )
    dataset = dataset.merge(
        profitandloss[["company_id", "year", "sales", "net_profit"]],
        on=["company_id", "year"],
        how="left",
    )
    dataset = dataset.merge(sectors, on="company_id", how="left")
    dataset = dataset.merge(companies, on="company_id", how="left")
    dataset = add_revenue_cagr_3yr(dataset, profitandloss)
    dataset = add_debt_to_equity_declining(dataset)
    return dataset


def latest_company_rows(df):
    if "year" not in df.columns:
        return df.copy()

    sortable = df.dropna(subset=["company_id", "year"]).copy()
    sortable["year"] = pd.to_numeric(sortable["year"], errors="coerce")
    return (
        sortable.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def run_quality_compounder(data=None, db_path="db/nifty100.db"):
    return _run_preset("quality_compounder", data, db_path)


def run_value_pick(data=None, db_path="db/nifty100.db"):
    return _run_preset("value_pick", data, db_path)


def run_growth_accelerator(data=None, db_path="db/nifty100.db"):
    return _run_preset("growth_accelerator", data, db_path)


def run_dividend_champion(data=None, db_path="db/nifty100.db"):
    return _run_preset("dividend_champion", data, db_path)


def run_debt_free_blue_chip(data=None, db_path="db/nifty100.db"):
    return _run_preset("debt_free_blue_chip", data, db_path)


def run_turnaround_watch(data=None, db_path="db/nifty100.db"):
    dataset = _load_or_copy(data, db_path)
    dataset = add_debt_to_equity_declining(dataset)
    return ScreenerEngine().run_preset("turnaround_watch", latest_company_rows(dataset))


def add_revenue_cagr_3yr(df, profitandloss):
    result = df.copy()
    if "revenue_cagr_3yr" not in result.columns:
        result["revenue_cagr_3yr"] = pd.NA

    cagr_lookup = {}
    for company_id, group in profitandloss.groupby("company_id"):
        records = group.sort_values("year").to_dict("records")
        for _, row in group.iterrows():
            year = row["year"]
            historical_records = [
                record
                for record in records
                if record.get("year") is not None and record["year"] <= year
            ]
            cagr = calculate_metric_cagrs(
                historical_records,
                "sales",
                "revenue",
                periods=(3,),
            )
            cagr_lookup[(company_id, year)] = cagr["revenue_cagr_3yr"]

    result["revenue_cagr_3yr"] = result.apply(
        lambda row: cagr_lookup.get((row.get("company_id"), row.get("year")), row.get("revenue_cagr_3yr")),
        axis=1,
    )
    return result


def add_debt_to_equity_declining(df):
    result = df.copy()
    result["debt_to_equity_declining"] = False
    if not {"company_id", "year", "debt_to_equity"}.issubset(result.columns):
        return result

    result["_year_sort"] = pd.to_numeric(result["year"], errors="coerce")
    result["_de_sort"] = pd.to_numeric(result["debt_to_equity"], errors="coerce")
    result = result.sort_values(["company_id", "_year_sort"])
    previous = result.groupby("company_id")["_de_sort"].shift(1)
    result["debt_to_equity_declining"] = result["_de_sort"] < previous
    return result.drop(columns=["_year_sort", "_de_sort"]).sort_index()


def ensure_composite_quality_score(df):
    if "composite_quality_score" in df.columns:
        return df

    metric_columns = [
        "return_on_equity_pct",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "operating_profit_margin_pct",
        "interest_coverage",
        "asset_turnover",
    ]
    available = [column for column in metric_columns if column in df.columns]
    if not available:
        df["composite_quality_score"] = 0
        return df

    normalized = pd.DataFrame(index=df.index)
    for column in available:
        values = pd.to_numeric(df[column], errors="coerce")
        max_value = values.max()
        normalized[column] = 0 if pd.isna(max_value) or max_value == 0 else values / max_value

    df["composite_quality_score"] = normalized.mean(axis=1).fillna(0) * 100
    return df


def _run_preset(preset_name, data=None, db_path="db/nifty100.db"):
    dataset = latest_company_rows(_load_or_copy(data, db_path))
    return ScreenerEngine().run_preset(preset_name, dataset)


def _load_or_copy(data, db_path):
    if data is not None:
        return data.copy()
    return load_screener_dataset(db_path)


def _apply_debt_to_equity_max(df, column, threshold):
    values = pd.to_numeric(df[column], errors="coerce")
    financials = _is_financials(df)
    return df[financials | (values < threshold)]


def _apply_debt_to_equity_equal(df, threshold):
    if "debt_to_equity" not in df.columns:
        return df.iloc[0:0]

    values = pd.to_numeric(df["debt_to_equity"], errors="coerce")
    return df[values == threshold]


def _effective_interest_coverage(df):
    values = pd.to_numeric(df["interest_coverage"], errors="coerce")
    if "icr_label" not in df.columns:
        return values

    return values.mask(df["icr_label"].eq("Debt Free"), float("inf"))


def _is_financials(df):
    if "broad_sector" not in df.columns:
        return pd.Series(False, index=df.index)

    return df["broad_sector"].astype(str).str.strip().str.upper().eq(FINANCIAL_SECTOR)

from pathlib import Path

import pandas as pd

from src.analytics.cagr import calculate_metric_cagrs
from src.analytics.cashflow import calculate_free_cash_flow
from src.analytics.ratios import (
    calculate_asset_turnover,
    calculate_debt_to_equity,
    calculate_interest_coverage_ratio,
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_capital_employed,
    calculate_return_on_equity,
)


EDGE_LOG_PATH = "output/ratio_edge_cases.log"
EDGE_LOG_HEADER = "issue_type,company_id,year,metric,computed_value,source_value,message\n"


def build_financial_ratios_table(tables, edge_log_path=EDGE_LOG_PATH):
    ratios = tables["financial_ratios"].copy()
    ratios = _prepare_ratio_columns(ratios)
    profitandloss = tables["profitandloss"].copy()
    balancesheet = tables["balancesheet"].copy()
    cashflow = tables["cashflow"].copy()
    companies = tables["companies"].copy()
    sectors = tables.get("sectors", pd.DataFrame()).copy()

    _reset_edge_log(edge_log_path)

    merged = _merge_financial_inputs(
        ratios,
        profitandloss,
        balancesheet,
        cashflow,
        companies,
        sectors,
    )

    cagr_lookup = _build_cagr_lookup(profitandloss)
    latest_year_by_company = (
        profitandloss.dropna(subset=["company_id", "year"])
        .groupby("company_id")["year"]
        .max()
        .to_dict()
    )

    for index, row in merged.iterrows():
        company_id = row["company_id"]
        year = row["year"]

        ratios.at[index, "net_profit_margin_pct"] = _prefer_computed(
            calculate_net_profit_margin(row.get("net_profit"), row.get("sales")),
            ratios.at[index, "net_profit_margin_pct"],
        )
        ratios.at[index, "operating_profit_margin_pct"] = _prefer_computed(
            calculate_operating_profit_margin(
                row.get("operating_profit"),
                row.get("sales"),
                row.get("opm_percentage"),
                company_id,
            ),
            ratios.at[index, "operating_profit_margin_pct"],
        )
        ratios.at[index, "return_on_equity_pct"] = _prefer_computed(
            calculate_return_on_equity(
                row.get("net_profit"),
                row.get("equity_capital"),
                row.get("reserves"),
            ),
            ratios.at[index, "return_on_equity_pct"],
        )
        ratios.at[index, "debt_to_equity"] = _prefer_computed(
            calculate_debt_to_equity(
                row.get("borrowings"),
                row.get("equity_capital"),
                row.get("reserves"),
            ),
            ratios.at[index, "debt_to_equity"],
        )
        ratios.at[index, "interest_coverage"] = _prefer_computed(
            calculate_interest_coverage_ratio(
                row.get("operating_profit"),
                row.get("other_income"),
                row.get("interest"),
            ),
            ratios.at[index, "interest_coverage"],
        )
        ratios.at[index, "asset_turnover"] = _prefer_computed(
            calculate_asset_turnover(row.get("sales"), row.get("total_assets")),
            ratios.at[index, "asset_turnover"],
        )
        ratios.at[index, "free_cash_flow_cr"] = _prefer_computed(
            calculate_free_cash_flow(
                row.get("operating_activity"),
                row.get("investing_activity"),
            ),
            ratios.at[index, "free_cash_flow_cr"],
        )
        ratios.at[index, "capex_cr"] = _prefer_computed(
            _abs_or_none(row.get("investing_activity")),
            ratios.at[index, "capex_cr"],
        )
        ratios.at[index, "earnings_per_share"] = _prefer_computed(
            row.get("eps"),
            ratios.at[index, "earnings_per_share"],
        )
        ratios.at[index, "book_value_per_share"] = _prefer_computed(
            _book_value_per_share(
                row.get("equity_capital"),
                row.get("reserves"),
            ),
            ratios.at[index, "book_value_per_share"],
        )
        ratios.at[index, "dividend_payout_ratio_pct"] = _prefer_computed(
            row.get("dividend_payout"),
            ratios.at[index, "dividend_payout_ratio_pct"],
        )
        ratios.at[index, "total_debt_cr"] = _prefer_computed(
            row.get("borrowings"),
            ratios.at[index, "total_debt_cr"],
        )
        ratios.at[index, "cash_from_operations_cr"] = _prefer_computed(
            row.get("operating_activity"),
            ratios.at[index, "cash_from_operations_cr"],
        )

        for column, value in cagr_lookup.get((company_id, year), {}).items():
            ratios.at[index, column] = value

        ratios.at[index, "composite_quality_score"] = _composite_quality_score(
            ratios.loc[index],
            row.get("broad_sector"),
        )

        if year == latest_year_by_company.get(company_id):
            _log_latest_roe_roce_edge_cases(
                edge_log_path,
                company_id,
                year,
                row,
            )

    return ratios


def _prepare_ratio_columns(ratios):
    computed_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for column in computed_columns:
        if column not in ratios.columns:
            ratios[column] = pd.NA
        ratios[column] = pd.to_numeric(ratios[column], errors="coerce").astype("Float64")

    for column in [
        "revenue_cagr_5yr_flag",
        "pat_cagr_5yr_flag",
        "eps_cagr_5yr_flag",
    ]:
        if column not in ratios.columns:
            ratios[column] = pd.NA

    return ratios


def _merge_financial_inputs(
    ratios,
    profitandloss,
    balancesheet,
    cashflow,
    companies,
    sectors,
):
    profitandloss = _dedupe_by_company_year(profitandloss)
    balancesheet = _dedupe_by_company_year(balancesheet)
    cashflow = _dedupe_by_company_year(cashflow)

    merged = ratios.merge(
        profitandloss,
        on=["company_id", "year"],
        how="left",
        suffixes=("", "_pl"),
    )
    merged = merged.merge(
        balancesheet,
        on=["company_id", "year"],
        how="left",
        suffixes=("", "_bs"),
    )
    merged = merged.merge(
        cashflow,
        on=["company_id", "year"],
        how="left",
        suffixes=("", "_cf"),
    )

    company_columns = [
        column
        for column in ["company_id", "roce_percentage", "roe_percentage"]
        if column in companies.columns
    ]
    if company_columns:
        merged = merged.merge(
            companies[company_columns],
            on="company_id",
            how="left",
            suffixes=("", "_company"),
        )

    if not sectors.empty and "broad_sector" in sectors.columns:
        merged = merged.merge(
            sectors[["company_id", "broad_sector"]],
            on="company_id",
            how="left",
        )

    return merged


def _dedupe_by_company_year(df):
    if "company_id" not in df.columns or "year" not in df.columns:
        return df

    return df.drop_duplicates(subset=["company_id", "year"], keep="last")


def _build_cagr_lookup(profitandloss):
    lookup = {}
    for company_id, group in profitandloss.groupby("company_id"):
        records = group.sort_values("year").to_dict("records")
        for _, row in group.iterrows():
            year = row["year"]
            historical_records = [
                record
                for record in records
                if record.get("year") is not None and record["year"] <= year
            ]
            revenue = calculate_metric_cagrs(
                historical_records,
                "sales",
                "revenue",
                periods=(5,),
            )
            pat = calculate_metric_cagrs(
                historical_records,
                "net_profit",
                "pat",
                periods=(5,),
            )
            eps = calculate_metric_cagrs(
                historical_records,
                "eps",
                "eps",
                periods=(5,),
            )
            lookup[(company_id, year)] = {
                "revenue_cagr_5yr": revenue["revenue_cagr_5yr"],
                "revenue_cagr_5yr_flag": revenue["revenue_cagr_5yr_flag"],
                "pat_cagr_5yr": pat["pat_cagr_5yr"],
                "pat_cagr_5yr_flag": pat["pat_cagr_5yr_flag"],
                "eps_cagr_5yr": eps["eps_cagr_5yr"],
                "eps_cagr_5yr_flag": eps["eps_cagr_5yr_flag"],
            }
    return lookup


def _log_latest_roe_roce_edge_cases(edge_log_path, company_id, year, row):
    computed_roe = calculate_return_on_equity(
        row.get("net_profit"),
        row.get("equity_capital"),
        row.get("reserves"),
    )
    computed_roce = calculate_return_on_capital_employed(
        _ebit(row),
        row.get("equity_capital"),
        row.get("reserves"),
        row.get("borrowings"),
    )

    _log_difference_if_needed(
        edge_log_path,
        company_id,
        year,
        "return_on_equity_pct",
        computed_roe,
        row.get("roe_percentage"),
    )
    _log_difference_if_needed(
        edge_log_path,
        company_id,
        year,
        "return_on_capital_employed_pct",
        computed_roce,
        row.get("roce_percentage"),
    )


def _log_difference_if_needed(
    edge_log_path,
    company_id,
    year,
    metric,
    computed_value,
    source_value,
):
    if computed_value is None or pd.isna(source_value):
        return

    difference = abs(float(computed_value) - float(source_value))
    if difference <= 5:
        return

    _append_edge_log(
        edge_log_path,
        "FORMULA_DISCREPANCY",
        company_id,
        year,
        metric,
        computed_value,
        source_value,
        f"Computed/source difference is {difference:.2f} percentage points",
    )


def _reset_edge_log(edge_log_path):
    path = Path(edge_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EDGE_LOG_HEADER, encoding="utf-8")


def _append_edge_log(
    edge_log_path,
    issue_type,
    company_id,
    year,
    metric,
    computed_value,
    source_value,
    message,
):
    with Path(edge_log_path).open("a", encoding="utf-8") as file:
        file.write(
            f"{issue_type},{company_id},{year},{metric},{computed_value},{source_value},{message}\n"
        )


def _prefer_computed(computed_value, existing_value):
    if computed_value is None or pd.isna(computed_value):
        return existing_value

    return computed_value


def _book_value_per_share(equity_capital, reserves):
    if equity_capital is None or pd.isna(equity_capital) or float(equity_capital) == 0:
        return None

    return (float(equity_capital) + float(reserves or 0)) / float(equity_capital)


def _abs_or_none(value):
    if value is None or pd.isna(value):
        return None

    return abs(float(value))


def _ebit(row):
    return float(row.get("operating_profit") or 0) + float(row.get("other_income") or 0)


def _composite_quality_score(row, broad_sector):
    checks = []
    checks.append(_score_threshold(row.get("return_on_equity_pct"), 15))

    if str(broad_sector).strip().upper() != "FINANCIALS":
        debt_to_equity = row.get("debt_to_equity")
        checks.append(None if pd.isna(debt_to_equity) else float(debt_to_equity) < 1)

    checks.append(_score_threshold(row.get("interest_coverage"), 1.5))
    checks.append(_score_threshold(row.get("asset_turnover"), 0))
    checks.append(_score_threshold(row.get("free_cash_flow_cr"), 0))

    valid_checks = [check for check in checks if check is not None]
    if not valid_checks:
        return None

    return (sum(1 for check in valid_checks if check) / len(valid_checks)) * 100


def _score_threshold(value, threshold):
    if value is None or pd.isna(value):
        return None

    return float(value) > threshold

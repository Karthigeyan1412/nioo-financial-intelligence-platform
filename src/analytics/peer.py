import logging
import sqlite3

import pandas as pd


LOGGER = logging.getLogger(__name__)

PEER_METRICS = [
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
    "eps_cagr_5yr",
    "interest_coverage",
    "asset_turnover",
]


def load_peer_inputs(db_path="db/nifty100.db"):
    with sqlite3.connect(db_path) as connection:
        financial_ratios = pd.read_sql_query(
            "SELECT * FROM financial_ratios",
            connection,
        )
        peer_groups = pd.read_sql_query(
            "SELECT peer_group_name, company_id FROM peer_groups",
            connection,
        )
        companies = (
            pd.read_sql_query(
                "SELECT company_id, roce_percentage FROM companies",
                connection,
            )
            if _table_exists(connection, "companies")
            else pd.DataFrame()
        )

    if "return_on_capital_employed_pct" not in financial_ratios.columns and not companies.empty:
        financial_ratios = financial_ratios.merge(
            companies,
            on="company_id",
            how="left",
        )
        financial_ratios = financial_ratios.rename(
            columns={"roce_percentage": "return_on_capital_employed_pct"}
        )

    return financial_ratios, peer_groups


def compute_peer_percentiles(
    financial_ratios,
    peer_groups,
    metrics=None,
):
    metrics = metrics or PEER_METRICS
    financial_ratios = _dedupe_financial_ratios(financial_ratios)
    peer_groups = peer_groups[["peer_group_name", "company_id"]].drop_duplicates()

    merged = financial_ratios.merge(
        peer_groups,
        on="company_id",
        how="left",
    )

    missing_peer_group = merged["peer_group_name"].isna()
    for company_id in sorted(merged.loc[missing_peer_group, "company_id"].dropna().unique()):
        LOGGER.warning("No peer group assigned: %s", company_id)

    ranked_source = merged[~missing_peer_group].copy()
    rows = []

    for metric in metrics:
        if metric not in ranked_source.columns:
            continue

        metric_data = ranked_source.dropna(subset=[metric, "year"]).copy()
        metric_data["value"] = pd.to_numeric(metric_data[metric], errors="coerce")
        metric_data = metric_data.dropna(subset=["value"])

        for _, group in metric_data.groupby(["peer_group_name", "year"], dropna=False):
            percentiles = _percent_rank(group["value"])
            if metric == "debt_to_equity":
                percentiles = 1 - percentiles

            for row_index, percentile in percentiles.items():
                source_row = group.loc[row_index]
                rows.append(
                    {
                        "company_id": source_row["company_id"],
                        "peer_group_name": source_row["peer_group_name"],
                        "metric": metric,
                        "value": source_row["value"],
                        "percentile_rank": percentile,
                        "year": int(source_row["year"]),
                    }
                )

    return pd.DataFrame(
        rows,
        columns=[
            "company_id",
            "peer_group_name",
            "metric",
            "value",
            "percentile_rank",
            "year",
        ],
    )


def populate_peer_percentiles(db_path="db/nifty100.db"):
    financial_ratios, peer_groups = load_peer_inputs(db_path)
    percentiles = compute_peer_percentiles(financial_ratios, peer_groups)

    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE IF EXISTS peer_percentiles")
        percentiles.to_sql(
            "peer_percentiles",
            connection,
            if_exists="replace",
            index=False,
        )

    return percentiles


def _percent_rank(values):
    count = len(values)
    if count == 1:
        return pd.Series(0.0, index=values.index)

    ranks = values.rank(method="min", ascending=True)
    return ((ranks - 1) / (count - 1)).clip(0, 1)


def _dedupe_financial_ratios(financial_ratios):
    if not {"company_id", "year"}.issubset(financial_ratios.columns):
        return financial_ratios.copy()

    return financial_ratios.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    ).copy()


def _table_exists(connection, table_name):
    return (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()[0]
        == 1
    )


if __name__ == "__main__":
    result = populate_peer_percentiles()
    print(f"Inserted peer percentile rows: {len(result)}")

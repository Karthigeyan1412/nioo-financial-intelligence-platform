import math
import os
import re
import sqlite3
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path("output") / "matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


RADAR_AXES = [
    ("return_on_equity_pct", "ROE"),
    ("return_on_capital_employed_pct", "ROCE"),
    ("net_profit_margin_pct", "NPM"),
    ("debt_to_equity", "D/E"),
    ("free_cash_flow_cr", "FCF Score"),
    ("pat_cagr_5yr", "PAT CAGR 5Y"),
    ("revenue_cagr_5yr", "Revenue CAGR 5Y"),
    ("composite_quality_score", "Composite"),
]


def generate_radar_charts(
    db_path="db/nifty100.db",
    output_dir="reports/radar_charts",
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _load_chart_data(db_path)
    latest = _latest_financial_rows(data["financial_ratios"])
    peer_groups = data["peer_groups"]
    peer_percentiles = data["peer_percentiles"]

    generated_paths = []
    nifty_average = _nifty_composite_average(latest)

    for _, row in latest.iterrows():
        company_id = row["company_id"]
        peer_group_name = _peer_group_for(peer_groups, company_id)
        output_path = output_dir / f"{_safe_filename(company_id)}_radar.png"

        if peer_group_name is None:
            _plot_standalone_composite_chart(
                company_id,
                row,
                nifty_average,
                output_path,
            )
        else:
            _plot_peer_radar_chart(
                company_id,
                peer_group_name,
                int(row["year"]),
                row,
                latest,
                peer_percentiles,
                output_path,
            )

        generated_paths.append(output_path)

    return generated_paths


def _load_chart_data(db_path):
    with sqlite3.connect(db_path) as connection:
        financial_ratios = pd.read_sql_query("SELECT * FROM financial_ratios", connection)
        companies = pd.read_sql_query(
            "SELECT company_id, roce_percentage FROM companies",
            connection,
        )
        peer_groups = pd.read_sql_query(
            "SELECT peer_group_name, company_id FROM peer_groups",
            connection,
        )
        peer_percentiles = pd.read_sql_query(
            "SELECT * FROM peer_percentiles",
            connection,
        )

    if "return_on_capital_employed_pct" not in financial_ratios.columns:
        financial_ratios = financial_ratios.merge(
            companies,
            on="company_id",
            how="left",
        ).rename(columns={"roce_percentage": "return_on_capital_employed_pct"})

    return {
        "financial_ratios": financial_ratios,
        "peer_groups": peer_groups,
        "peer_percentiles": peer_percentiles,
    }


def _latest_financial_rows(financial_ratios):
    latest = financial_ratios.dropna(subset=["company_id", "year"]).copy()
    latest["year"] = pd.to_numeric(latest["year"], errors="coerce")
    return (
        latest.sort_values(["company_id", "year"])
        .drop_duplicates(subset=["company_id"], keep="last")
        .reset_index(drop=True)
    )


def _peer_group_for(peer_groups, company_id):
    matches = peer_groups[peer_groups["company_id"].eq(company_id)]
    if matches.empty:
        return None
    return matches["peer_group_name"].iloc[0]


def _plot_peer_radar_chart(
    company_id,
    peer_group_name,
    year,
    row,
    latest,
    peer_percentiles,
    output_path,
):
    labels = [label for _, label in RADAR_AXES]
    company_values = _company_axis_values(company_id, year, row, peer_percentiles)
    peer_average_values = _peer_average_axis_values(
        peer_group_name,
        year,
        latest,
        peer_percentiles,
    )

    _plot_polar(
        title=f"{company_id} vs {peer_group_name} ({year})",
        labels=labels,
        company_values=company_values,
        reference_values=peer_average_values,
        reference_label="Peer average",
        output_path=output_path,
    )


def _plot_standalone_composite_chart(company_id, row, nifty_average, output_path):
    composite = _bounded_score(row.get("composite_quality_score")) / 100
    labels = ["Composite"]
    _plot_polar(
        title=f"{company_id} standalone composite",
        labels=labels,
        company_values=[composite],
        reference_values=[nifty_average],
        reference_label="Nifty 100 average",
        output_path=output_path,
    )


def _plot_polar(
    title,
    labels,
    company_values,
    reference_values,
    reference_label,
    output_path,
):
    values = company_values + company_values[:1]
    reference = reference_values + reference_values[:1]
    angles = _angles(len(labels))

    fig, axis = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    axis.plot(angles, values, linewidth=2, label="Company")
    axis.fill(angles, values, alpha=0.25)
    axis.plot(angles, reference, linestyle="--", linewidth=2, label=reference_label)
    axis.set_xticks(angles[:-1])
    axis.set_xticklabels(labels, fontsize=10)
    axis.set_ylim(0, 1)
    axis.set_yticks([0.25, 0.5, 0.75, 1.0])
    axis.set_yticklabels(["25", "50", "75", "100"], fontsize=9)
    axis.set_title(title, fontsize=14, pad=20)
    axis.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), fontsize=10)
    fig.tight_layout()
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def _company_axis_values(company_id, year, row, peer_percentiles):
    values = []
    for metric, _ in RADAR_AXES:
        if metric == "composite_quality_score":
            values.append(_bounded_score(row.get(metric)) / 100)
            continue

        metric_rows = peer_percentiles[
            peer_percentiles["company_id"].eq(company_id)
            & peer_percentiles["year"].eq(year)
            & peer_percentiles["metric"].eq(metric)
        ]
        if metric_rows.empty:
            values.append(0)
        else:
            values.append(float(metric_rows["percentile_rank"].iloc[0]))
    return values


def _peer_average_axis_values(peer_group_name, year, latest, peer_percentiles):
    values = []
    group_company_ids = peer_percentiles[
        peer_percentiles["peer_group_name"].eq(peer_group_name)
    ]["company_id"].unique()
    latest_group = latest[latest["company_id"].isin(group_company_ids)]

    for metric, _ in RADAR_AXES:
        if metric == "composite_quality_score":
            values.append(
                _bounded_score(latest_group["composite_quality_score"].mean()) / 100
            )
            continue

        metric_rows = peer_percentiles[
            peer_percentiles["peer_group_name"].eq(peer_group_name)
            & peer_percentiles["year"].eq(year)
            & peer_percentiles["metric"].eq(metric)
        ]
        values.append(float(metric_rows["percentile_rank"].mean()) if not metric_rows.empty else 0)
    return values


def _nifty_composite_average(latest):
    return _bounded_score(latest["composite_quality_score"].mean()) / 100


def _bounded_score(value):
    if pd.isna(value):
        return 0
    return max(0, min(float(value), 100))


def _angles(count):
    if count == 1:
        return [0, 2 * math.pi]
    return [index / float(count) * 2 * math.pi for index in range(count)] + [0]


def _safe_filename(company_id):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(company_id)).strip("_")


if __name__ == "__main__":
    paths = generate_radar_charts()
    print(f"Generated radar charts: {len(paths)}")

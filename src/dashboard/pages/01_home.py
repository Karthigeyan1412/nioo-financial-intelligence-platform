import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_home_snapshot


YEARS = [2019, 2020, 2021, 2022, 2023, 2024]


def main():
    st.title("Home")
    st.write("Market-wide Nifty 100 snapshot by financial year.")

    selected_year = st.sidebar.selectbox(
        "Financial year",
        YEARS,
        index=len(YEARS) - 1,
    )

    snapshot = get_home_snapshot(selected_year)
    if snapshot.empty:
        st.warning("No dashboard data available for the selected year.")
        return

    _render_kpi_cards(snapshot)
    _render_sector_distribution(snapshot)
    _render_top_companies(snapshot)


def _render_kpi_cards(snapshot):
    metrics = {
        "Average ROE": _format_percent(snapshot["return_on_equity_pct"].mean()),
        "Median P/E": _format_number(snapshot["pe_ratio"].median()),
        "Median D/E": _format_number(snapshot["debt_to_equity"].median()),
        "Total Companies": f"{snapshot['company_id'].nunique():,.0f}",
        "Median Revenue CAGR 5yr": _format_percent(snapshot["revenue_cagr_5yr"].median()),
        "Debt-Free Companies": f"{_debt_free_count(snapshot):,.0f}",
    }

    rows = [st.columns(3), st.columns(3)]
    for index, (label, value) in enumerate(metrics.items()):
        rows[index // 3][index % 3].metric(label, value)


def _render_sector_distribution(snapshot):
    sector_counts = (
        snapshot.dropna(subset=["broad_sector"])
        .groupby("broad_sector", as_index=False)["company_id"]
        .nunique()
        .rename(columns={"company_id": "company_count"})
        .sort_values("company_count", ascending=False)
    )

    st.subheader("Sector Distribution")
    fig = px.pie(
        sector_counts,
        names="broad_sector",
        values="company_count",
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
    st.plotly_chart(fig, width="stretch")


def _render_top_companies(snapshot):
    st.subheader("Top 5 Companies by Composite Quality Score")
    top_companies = (
        snapshot.sort_values("composite_quality_score", ascending=False, na_position="last")
        .head(5)[
            [
                "company_id",
                "company_name",
                "broad_sector",
                "return_on_equity_pct",
                "debt_to_equity",
                "revenue_cagr_5yr",
                "composite_quality_score",
            ]
        ]
        .rename(
            columns={
                "company_id": "Ticker",
                "company_name": "Company",
                "broad_sector": "Sector",
                "return_on_equity_pct": "ROE %",
                "debt_to_equity": "Debt to Equity",
                "revenue_cagr_5yr": "Revenue CAGR 5yr %",
                "composite_quality_score": "Composite Score",
            }
        )
    )
    st.dataframe(top_companies, width="stretch", hide_index=True)


def _debt_free_count(snapshot):
    debt_to_equity = pd.to_numeric(snapshot["debt_to_equity"], errors="coerce")
    return int((debt_to_equity == 0).sum())


def _format_percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def _format_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


main()

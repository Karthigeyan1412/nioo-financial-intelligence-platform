from html import escape

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.dashboard.utils.db import (
    get_company_directory,
    get_company_profile,
    get_latest_company_kpis,
    get_pros_cons,
    get_revenue_profit_trend,
    get_roe_roce_trend,
)


NOT_FOUND_MESSAGE = "Ticker not found — please try another"


def main():
    st.title("Company Profile")
    st.write("Company fundamentals, profitability trends, and qualitative notes.")

    directory = get_company_directory()
    selected_ticker = _company_search(directory)

    if selected_ticker is None:
        st.info("Search by company name or ticker to view a profile.")
        return

    profile = get_company_profile(selected_ticker)
    if profile.empty:
        st.error(NOT_FOUND_MESSAGE)
        return

    profile_row = profile.iloc[0]
    _render_profile_card(profile_row)
    _render_kpi_cards(selected_ticker)
    _render_revenue_profit_chart(selected_ticker)
    _render_roe_roce_chart(selected_ticker)
    _render_pros_cons(selected_ticker)


def _company_search(directory):
    suggestions = [
        f"{row.company_id} - {row.company_name}"
        for row in directory.itertuples(index=False)
    ]

    selected = st.selectbox(
        "Autocomplete suggestions",
        suggestions,
        index=None,
        placeholder="Choose a company",
    )
    manual_query = st.text_input("Search box", placeholder="Type company name or ticker")

    if selected:
        return selected.split(" - ", 1)[0].strip()

    query = manual_query.strip()
    if not query:
        return None

    ticker_match = directory[
        directory["company_id"].astype(str).str.upper().eq(query.upper())
    ]
    if not ticker_match.empty:
        return ticker_match["company_id"].iloc[0]

    name_match = directory[
        directory["company_name"].astype(str).str.lower().str.contains(query.lower(), na=False)
    ]
    if not name_match.empty:
        return name_match["company_id"].iloc[0]

    return query.upper()


def _render_profile_card(row):
    st.subheader(row["company_name"])
    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:16px; margin-bottom:16px;">
            <strong>Company Name:</strong> {escape(str(row.get("company_name", "N/A")))}<br>
            <strong>Sector:</strong> {escape(str(row.get("broad_sector", "N/A")))}<br>
            <strong>Sub-sector:</strong> {escape(str(row.get("sub_sector", "N/A")))}<br>
            <strong>NSE Ticker:</strong> {escape(str(row.get("company_id", "N/A")))}<br><br>
            <strong>About:</strong> {escape(str(row.get("about_company", "N/A")))}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_cards(ticker):
    kpis = get_latest_company_kpis(ticker)
    if kpis.empty:
        st.warning("No KPI data available for this company.")
        return

    row = kpis.iloc[0]
    metrics = {
        "ROE": _format_percent(row.get("return_on_equity_pct")),
        "ROCE": _format_percent(row.get("return_on_capital_employed_pct")),
        "Net Profit Margin": _format_percent(row.get("net_profit_margin_pct")),
        "Debt to Equity": _format_number(row.get("debt_to_equity")),
        "Revenue CAGR 5yr": _format_percent(row.get("revenue_cagr_5yr")),
        "Free Cash Flow": _format_currency(row.get("free_cash_flow_cr")),
    }

    rows = [st.columns(3), st.columns(3)]
    for index, (label, value) in enumerate(metrics.items()):
        rows[index // 3][index % 3].metric(label, value)


def _render_revenue_profit_chart(ticker):
    trend = get_revenue_profit_trend(ticker)
    st.subheader("Revenue and Net Profit")
    if trend.empty:
        st.info("No revenue/profit trend data available.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["year"], y=trend["sales"], name="Revenue"))
    fig.add_trace(go.Bar(x=trend["year"], y=trend["net_profit"], name="Net Profit"))
    fig.update_layout(
        barmode="group",
        xaxis_title="Year",
        yaxis_title="Amount",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, width="stretch")


def _render_roe_roce_chart(ticker):
    trend = get_roe_roce_trend(ticker)
    st.subheader("ROE and ROCE")
    if trend.empty:
        st.info("No ROE/ROCE trend data available.")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=trend["year"],
            y=trend["return_on_equity_pct"],
            mode="lines+markers",
            name="ROE",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=trend["year"],
            y=trend["return_on_capital_employed_pct"],
            mode="lines+markers",
            name="ROCE",
        ),
        secondary_y=True,
    )
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text="ROE %", secondary_y=False)
    fig.update_yaxes(title_text="ROCE %", secondary_y=True)
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, width="stretch")


def _render_pros_cons(ticker):
    notes = get_pros_cons(ticker)
    st.subheader("Pros and Cons")
    if notes.empty:
        st.info("No pros and cons available for this company.")
        return

    pros = _split_notes(notes["pros"].dropna().tolist())
    cons = _split_notes(notes["cons"].dropna().tolist())
    left, right = st.columns(2)
    with left:
        st.markdown("**Pros**")
        _render_badges(pros, "#dcfce7", "#166534", "✓")
    with right:
        st.markdown("**Cons**")
        _render_badges(cons, "#fee2e2", "#991b1b", "✕")


def _render_badges(items, background, color, icon):
    if not items:
        st.write("None available")
        return

    for item in items:
        st.markdown(
            f"""
            <span style="
                display:inline-block;
                background:{background};
                color:{color};
                border-radius:999px;
                padding:6px 10px;
                margin:4px 0;
                font-size:0.92rem;">
                {icon} {escape(item)}
            </span>
            """,
            unsafe_allow_html=True,
        )


def _split_notes(values):
    notes = []
    for value in values:
        for part in str(value).replace("\r", "\n").split("\n"):
            cleaned = part.strip(" -;\t")
            if cleaned:
                notes.append(cleaned)
    return notes


def _format_percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}%"


def _format_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def _format_currency(value):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):,.2f} Cr"


main()

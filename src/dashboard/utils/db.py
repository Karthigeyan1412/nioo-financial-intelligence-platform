from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


DB_PATH = Path("db/nifty100.db")


def _query(sql, params=None):
    connection = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, connection, params=params or {})
    finally:
        connection.close()


@st.cache_data(ttl=600)
def get_companies():
    return _query(
        """
        SELECT *
        FROM companies
        ORDER BY company_id
        """
    )


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    params = {"ticker": ticker}
    sql = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = :ticker
    """
    if year is not None:
        sql += " AND year = :year"
        params["year"] = year
    sql += " ORDER BY year"
    return _query(sql, params)


@st.cache_data(ttl=600)
def get_pl(ticker):
    return _query(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = :ticker
        ORDER BY year
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_bs(ticker):
    return _query(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = :ticker
        ORDER BY year
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_cf(ticker):
    return _query(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = :ticker
        ORDER BY year
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_sectors():
    return _query(
        """
        SELECT *
        FROM sectors
        ORDER BY broad_sector, company_id
        """
    )


@st.cache_data(ttl=600)
def get_peers(group_name):
    return _query(
        """
        SELECT
            pg.peer_group_name,
            pg.company_id,
            c.company_name,
            pg.is_benchmark
        FROM peer_groups pg
        LEFT JOIN companies c
            ON c.company_id = pg.company_id
        WHERE pg.peer_group_name = :group_name
        ORDER BY pg.is_benchmark DESC, pg.company_id
        """,
        {"group_name": group_name},
    )


@st.cache_data(ttl=600)
def get_valuation(ticker):
    return _query(
        """
        SELECT *
        FROM market_cap
        WHERE company_id = :ticker
        ORDER BY year
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_home_snapshot(year):
    return _query(
        """
        SELECT
            fr.company_id,
            c.company_name,
            s.broad_sector,
            fr.return_on_equity_pct,
            fr.debt_to_equity,
            fr.revenue_cagr_5yr,
            fr.composite_quality_score,
            mc.pe_ratio
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON c.company_id = fr.company_id
        LEFT JOIN sectors s
            ON s.company_id = fr.company_id
        LEFT JOIN market_cap mc
            ON mc.company_id = fr.company_id
           AND mc.year = fr.year
        WHERE fr.year = :year
        """,
        {"year": year},
    )


@st.cache_data(ttl=600)
def get_company_directory():
    return _query(
        """
        SELECT
            c.company_id,
            c.company_name,
            c.about_company,
            s.broad_sector,
            s.sub_sector
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.company_id
        ORDER BY c.company_name
        """
    )


@st.cache_data(ttl=600)
def get_company_profile(ticker):
    return _query(
        """
        SELECT
            c.company_id,
            c.company_name,
            c.about_company,
            c.roce_percentage,
            c.roe_percentage,
            s.broad_sector,
            s.sub_sector
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.company_id
        WHERE UPPER(c.company_id) = UPPER(:ticker)
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_latest_company_kpis(ticker):
    return _query(
        """
        SELECT
            fr.company_id,
            fr.year,
            fr.return_on_equity_pct,
            c.roce_percentage AS return_on_capital_employed_pct,
            fr.net_profit_margin_pct,
            fr.debt_to_equity,
            fr.revenue_cagr_5yr,
            fr.free_cash_flow_cr
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON c.company_id = fr.company_id
        WHERE UPPER(fr.company_id) = UPPER(:ticker)
        ORDER BY fr.year DESC
        LIMIT 1
        """,
        {"ticker": ticker},
    )


@st.cache_data(ttl=600)
def get_revenue_profit_trend(ticker):
    return _query(
        """
        SELECT
            year,
            sales,
            net_profit
        FROM profitandloss
        WHERE UPPER(company_id) = UPPER(:ticker)
        ORDER BY year DESC
        LIMIT 10
        """,
        {"ticker": ticker},
    ).sort_values("year")


@st.cache_data(ttl=600)
def get_roe_roce_trend(ticker):
    return _query(
        """
        SELECT
            fr.year,
            fr.return_on_equity_pct,
            CASE
                WHEN (bs.equity_capital + bs.reserves + bs.borrowings) > 0
                THEN (pl.operating_profit / (bs.equity_capital + bs.reserves + bs.borrowings)) * 100
                ELSE NULL
            END AS return_on_capital_employed_pct
        FROM financial_ratios fr
        LEFT JOIN profitandloss pl
            ON pl.company_id = fr.company_id
           AND pl.year = fr.year
        LEFT JOIN balancesheet bs
            ON bs.company_id = fr.company_id
           AND bs.year = fr.year
        WHERE UPPER(fr.company_id) = UPPER(:ticker)
        ORDER BY fr.year DESC
        LIMIT 10
        """,
        {"ticker": ticker},
    ).sort_values("year")


@st.cache_data(ttl=600)
def get_pros_cons(ticker):
    return _query(
        """
        SELECT pros, cons
        FROM prosandcons
        WHERE UPPER(company_id) = UPPER(:ticker)
        """,
        {"ticker": ticker},
    )

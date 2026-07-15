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

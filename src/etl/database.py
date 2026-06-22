import logging
import sqlite3
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)

REFERENCE_TABLES = {
    "analysis",
    "balancesheet",
    "cashflow",
    "documents",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "profitandloss",
    "prosandcons",
    "sectors",
    "stock_prices",
}


def connect(db_path="db/nifty100.db"):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def load_sqlite(tables, db_path="db/nifty100.db"):
    """
    Create target tables, load all DataFrames, and return database row counts.
    """

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        _drop_existing_tables(connection)

        for table_name, df in tables.items():
            LOGGER.info("Creating table %s", table_name)
            connection.execute(_build_create_table_sql(table_name, df))

        for table_name, df in tables.items():
            LOGGER.info("Loading %s rows into %s", len(df), table_name)
            df.to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
            )

        connection.commit()
        connection.execute("PRAGMA foreign_keys = ON")
        return get_row_counts(connection, tables.keys())


def get_row_counts(connection, table_names):
    counts = {}
    for table_name in table_names:
        counts[table_name] = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]
    return counts


def foreign_key_check(db_path="db/nifty100.db"):
    with connect(db_path) as connection:
        rows = connection.execute("PRAGMA foreign_key_check").fetchall()

    return [
        {
            "table_name": row[0],
            "row_id": row[1],
            "parent_table": row[2],
            "foreign_key_id": row[3],
        }
        for row in rows
    ]


def export_schema(db_path="db/nifty100.db", schema_path="db/schema.sql"):
    schema_path = Path(schema_path)
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    with connect(db_path) as connection:
        statements = [
            row[0]
            for row in connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
            if row[0]
        ]

    schema_path.write_text(";\n\n".join(statements) + ";\n", encoding="utf-8")
    return schema_path


def _drop_existing_tables(connection):
    table_names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    ]

    for table_name in table_names:
        connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')


def _build_create_table_sql(table_name, df):
    columns = [_column_definition(column, df[column]) for column in df.columns]
    constraints = []

    if table_name == "companies" and "company_id" in df.columns:
        constraints.append('PRIMARY KEY ("company_id")')

    if table_name in REFERENCE_TABLES and "company_id" in df.columns:
        constraints.append(
            'FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id")'
        )

    all_definitions = columns + constraints
    definition_sql = ",\n    ".join(all_definitions)
    return f'CREATE TABLE "{table_name}" (\n    {definition_sql}\n)'


def _column_definition(column, series):
    sqlite_type = _sqlite_type(series)
    return f'"{column}" {sqlite_type}'


def _sqlite_type(series):
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"

    if pd.api.types.is_float_dtype(series):
        return "REAL"

    if pd.api.types.is_bool_dtype(series):
        return "INTEGER"

    return "TEXT"

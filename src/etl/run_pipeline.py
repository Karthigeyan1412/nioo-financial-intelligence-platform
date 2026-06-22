import logging
from pathlib import Path

import pandas as pd

from src.etl.database import export_schema, foreign_key_check, load_sqlite
from src.etl.loader import ExcelLoader
from src.etl.normaliser import normalize_dataset
from src.etl.validator import DataQualityValidator


LOGGER = logging.getLogger(__name__)

DATASETS = {
    "analysis": ("data/main/analysis.xlsx", 1),
    "companies": ("data/main/companies.xlsx", 1),
    "balancesheet": ("data/main/balancesheet.xlsx", 1),
    "cashflow": ("data/main/cashflow.xlsx", 1),
    "documents": ("data/main/documents.xlsx", 1),
    "profitandloss": ("data/main/profitandloss.xlsx", 1),
    "prosandcons": ("data/main/prosandcons.xlsx", 1),
    "financial_ratios": ("data/supporting/financial_ratios.xlsx", 0),
    "market_cap": ("data/supporting/market_cap.xlsx", 0),
    "peer_groups": ("data/supporting/peer_groups.xlsx", 0),
    "sectors": ("data/supporting/sectors.xlsx", 0),
    "stock_prices": ("data/supporting/stock_prices.xlsx", 0),
}


def run_pipeline(
    db_path="db/nifty100.db",
    audit_path="output/load_audit.csv",
    validation_path="output/validation_failures.csv",
):
    _configure_logging()

    loader = ExcelLoader()
    tables = {}
    audit_rows = []

    LOGGER.info("Starting full ETL load for %s datasets", len(DATASETS))

    for table_name, (file_path, header) in DATASETS.items():
        try:
            raw, normalized = _read_and_normalize(loader, table_name, file_path, header)
            tables[table_name] = normalized
            audit_rows.append(
                _audit_row(
                    table_name=table_name,
                    source_file=file_path,
                    source_row_count=len(raw),
                    db_row_count=0,
                    status="READ_SUCCESS",
                    message="Source file read and normalized",
                )
            )
        except Exception as exc:
            LOGGER.exception("Failed reading %s", table_name)
            audit_rows.append(
                _audit_row(
                    table_name=table_name,
                    source_file=file_path,
                    source_row_count=0,
                    db_row_count=0,
                    status="ERROR",
                    message=str(exc),
                )
            )

    db_row_counts = {}
    written_schema = None
    if tables:
        db_row_counts = load_sqlite(tables, db_path)
        written_schema = export_schema(db_path)
        LOGGER.info("Loaded SQLite database: %s", db_path)

    fk_violations = foreign_key_check(db_path) if tables else []
    fk_counts = _foreign_key_counts_by_table(fk_violations)

    final_audit_rows = []
    for row in audit_rows:
        table_name = row["table_name"]
        if row["status"] == "ERROR":
            final_audit_rows.append(row)
            continue

        db_count = db_row_counts.get(table_name, 0)
        source_count = row["source_row_count"]
        fk_count = fk_counts.get(table_name, 0)

        if source_count != db_count:
            status = "ROW_COUNT_MISMATCH"
            message = f"Source rows {source_count} != database rows {db_count}"
        elif fk_count:
            status = "FK_VIOLATIONS"
            message = f"{fk_count} SQLite foreign key violation(s)"
        else:
            status = "SUCCESS"
            message = "Loaded successfully"

        row.update(
            {
                "row_count": db_count,
                "db_row_count": db_count,
                "fk_violation_count": fk_count,
                "status": status,
                "message": message,
            }
        )
        final_audit_rows.append(row)

    written_audit = write_load_audit(final_audit_rows, audit_path)
    written_failures = DataQualityValidator().write_failures(tables, validation_path)

    LOGGER.info("Wrote load audit: %s", written_audit)
    LOGGER.info("Wrote validation failures: %s", written_failures)

    return {
        "tables": tables,
        "db_path": Path(db_path),
        "schema_path": written_schema,
        "audit_path": written_audit,
        "validation_path": written_failures,
        "foreign_key_violations": fk_violations,
    }


def write_load_audit(rows, audit_path="output/load_audit.csv"):
    audit_path = Path(audit_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "table_name",
        "row_count",
        "status",
        "source_file",
        "source_row_count",
        "db_row_count",
        "fk_violation_count",
        "message",
    ]

    pd.DataFrame(rows, columns=columns).to_csv(audit_path, index=False)
    return audit_path


def _read_and_normalize(loader, table_name, file_path, header):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    LOGGER.info("Reading %s from %s", table_name, file_path)
    raw = loader.load_excel(path, header=header)
    normalized = normalize_dataset(table_name, raw)
    return raw, normalized


def _audit_row(
    table_name,
    source_file,
    source_row_count,
    db_row_count,
    status,
    message,
):
    return {
        "table_name": table_name,
        "row_count": db_row_count,
        "status": status,
        "source_file": source_file,
        "source_row_count": source_row_count,
        "db_row_count": db_row_count,
        "fk_violation_count": 0,
        "message": message,
    }


def _foreign_key_counts_by_table(violations):
    counts = {}
    for violation in violations:
        table_name = violation["table_name"]
        counts[table_name] = counts.get(table_name, 0) + 1
    return counts


def _configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


if __name__ == "__main__":
    result = run_pipeline()
    print(f"Loaded SQLite database: {result['db_path']}")
    print(f"Wrote SQLite schema: {result['schema_path']}")
    print(f"Wrote load audit: {result['audit_path']}")
    print(f"Wrote validation failures: {result['validation_path']}")
    print(f"SQLite foreign key violations: {len(result['foreign_key_violations'])}")

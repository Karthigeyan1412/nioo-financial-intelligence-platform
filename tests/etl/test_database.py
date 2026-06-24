import pandas as pd

from src.etl.database import foreign_key_check, load_sqlite


def test_foreign_key_check_reports_invalid_company_reference(tmp_path):
    db_path = tmp_path / "test.db"
    tables = {
        "companies": pd.DataFrame({"company_id": ["TCS"]}),
        "cashflow": pd.DataFrame({"company_id": ["UNKNOWN"], "year": [2024]}),
    }

    load_sqlite(tables, db_path)
    violations = foreign_key_check(db_path)

    assert len(violations) == 1
    assert violations[0]["table_name"] == "cashflow"
    assert violations[0]["parent_table"] == "companies"

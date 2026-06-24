import pandas as pd

from src.etl.company_mapper import (
    apply_company_mappings,
    build_fk_resolution_report,
    find_missing_company_ids,
)


def test_apply_company_mappings_replaces_known_aliases_and_logs_counts():
    tables = {
        "companies": pd.DataFrame({"company_id": ["ATGL"]}),
        "cashflow": pd.DataFrame({"company_id": ["AGTL", "ATGL", "AGTL"]}),
    }

    mapped_tables, replacement_log = apply_company_mappings(tables)

    assert mapped_tables["cashflow"]["company_id"].tolist() == ["ATGL", "ATGL", "ATGL"]
    assert replacement_log.loc[0, "source_table"] == "cashflow"
    assert replacement_log.loc[0, "original_company_id"] == "AGTL"
    assert replacement_log.loc[0, "mapped_company_id"] == "ATGL"
    assert replacement_log.loc[0, "replacement_count"] == 2


def test_find_missing_company_ids_reports_unresolved_references():
    tables = {
        "companies": pd.DataFrame({"company_id": ["TCS"]}),
        "balancesheet": pd.DataFrame({"company_id": ["TCS", "WIPRO", "WIPRO"]}),
    }

    missing = find_missing_company_ids(tables)

    assert missing.to_dict("records") == [
        {
            "company_id": "WIPRO",
            "table_name": "balancesheet",
            "occurrences": 2,
        }
    ]


def test_build_fk_resolution_report_marks_resolved_and_unresolved_ids():
    before = pd.DataFrame(
        [
            {"company_id": "AGTL", "table_name": "cashflow", "occurrences": 2},
            {"company_id": "WIPRO", "table_name": "cashflow", "occurrences": 1},
        ]
    )
    after = pd.DataFrame(
        [
            {"company_id": "WIPRO", "table_name": "cashflow", "occurrences": 1},
        ]
    )

    report = build_fk_resolution_report(before, after)

    statuses = {
        (row["company_id"], row["affected_table"]): row["resolution_status"]
        for _, row in report.iterrows()
    }
    assert statuses[("AGTL", "cashflow")] == "RESOLVED"
    assert statuses[("WIPRO", "cashflow")] == "UNRESOLVED"

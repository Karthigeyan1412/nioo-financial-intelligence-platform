from collections import Counter
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path

import pandas as pd


DEFAULT_COMPANY_ID_MAPPINGS = {
    "AGTL": "ATGL",
}

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


def standardize_company_id(company_id):
    if pd.isna(company_id):
        return None

    text = str(company_id).strip().upper()
    if not text or text in {"NAN", "NONE"}:
        return None

    return text


def apply_company_mappings(tables, mappings=None):
    mappings = _standardize_mapping(mappings or DEFAULT_COMPANY_ID_MAPPINGS)
    mapped_tables = {name: df.copy() for name, df in tables.items()}
    replacement_rows = []

    for table_name, df in mapped_tables.items():
        if table_name == "companies" or "company_id" not in df.columns:
            continue

        original = df["company_id"].apply(standardize_company_id)
        mapped = original.replace(mappings)
        df["company_id"] = mapped

        for source_id, target_id in mappings.items():
            count = int((original == source_id).sum())
            if count:
                replacement_rows.append(
                    {
                        "source_table": table_name,
                        "original_company_id": source_id,
                        "mapped_company_id": target_id,
                        "replacement_count": count,
                    }
                )

    return mapped_tables, pd.DataFrame(
        replacement_rows,
        columns=[
            "source_table",
            "original_company_id",
            "mapped_company_id",
            "replacement_count",
        ],
    )


def build_mapping_candidates(missing_company_ids, known_company_ids, mappings=None):
    mappings = _standardize_mapping(mappings or DEFAULT_COMPANY_ID_MAPPINGS)
    known = {standardize_company_id(value) for value in known_company_ids}
    known.discard(None)

    rows = []
    for missing_id in sorted({standardize_company_id(value) for value in missing_company_ids}):
        if missing_id is None:
            continue

        explicit_candidate = mappings.get(missing_id)
        if explicit_candidate in known:
            rows.append(
                {
                    "missing_company_id": missing_id,
                    "candidate_company_id": explicit_candidate,
                    "confidence_score": 0.95,
                    "reason": "Explicit high-confidence ticker correction",
                }
            )
            continue

        close_match = _closest_match(missing_id, known)
        if close_match is None:
            rows.append(
                {
                    "missing_company_id": missing_id,
                    "candidate_company_id": "",
                    "confidence_score": 0.0,
                    "reason": "No high-confidence candidate found in companies table",
                }
            )
            continue

        candidate, score = close_match
        if score >= 0.9:
            rows.append(
                {
                    "missing_company_id": missing_id,
                    "candidate_company_id": candidate,
                    "confidence_score": round(score, 2),
                    "reason": "High string similarity to companies.id",
                }
            )
        else:
            rows.append(
                {
                    "missing_company_id": missing_id,
                    "candidate_company_id": candidate,
                    "confidence_score": round(score, 2),
                    "reason": "Candidate below automatic mapping threshold",
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "missing_company_id",
            "candidate_company_id",
            "confidence_score",
            "reason",
        ],
    )


def find_missing_company_ids(tables):
    companies = tables.get("companies", pd.DataFrame())
    if "company_id" not in companies.columns:
        known_ids = set()
    else:
        known_ids = set(companies["company_id"].apply(standardize_company_id).dropna())

    rows = []
    for table_name, df in tables.items():
        if table_name == "companies" or "company_id" not in df.columns:
            continue

        values = df["company_id"].apply(standardize_company_id).dropna()
        missing = values[~values.isin(known_ids)]
        counts = Counter(missing)

        for company_id, count in sorted(counts.items()):
            rows.append(
                {
                    "company_id": company_id,
                    "table_name": table_name,
                    "occurrences": int(count),
                }
            )

    return pd.DataFrame(rows, columns=["company_id", "table_name", "occurrences"])


def build_fk_resolution_report(before_missing, after_missing):
    before_lookup = _missing_lookup(before_missing)
    after_lookup = _missing_lookup(after_missing)

    keys = sorted(set(before_lookup) | set(after_lookup))
    rows = []
    for company_id, table_name in keys:
        before_count = before_lookup.get((company_id, table_name), 0)
        after_count = after_lookup.get((company_id, table_name), 0)

        if before_count and not after_count:
            status = "RESOLVED"
        elif before_count != after_count:
            status = "PARTIALLY_RESOLVED"
        else:
            status = "UNRESOLVED"

        rows.append(
            {
                "company_id": company_id,
                "affected_table": table_name,
                "before_count": before_count,
                "after_count": after_count,
                "resolution_status": status,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "company_id",
            "affected_table",
            "before_count",
            "after_count",
            "resolution_status",
        ],
    )


def write_mapping_reports(
    before_tables,
    after_tables,
    output_dir="output",
    mappings=None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    before_missing = find_missing_company_ids(before_tables)
    after_missing = find_missing_company_ids(after_tables)

    known_ids = before_tables["companies"]["company_id"]
    candidates = build_mapping_candidates(
        before_missing["company_id"].unique(),
        known_ids,
        mappings=mappings,
    )
    resolution = build_fk_resolution_report(before_missing, after_missing)

    candidates_path = output_dir / "company_id_mapping_candidates.csv"
    resolution_path = output_dir / "fk_resolution_report.csv"
    unresolved_path = output_dir / "unresolved_company_ids.csv"
    missing_path = output_dir / "missing_company_ids.csv"

    candidates.to_csv(candidates_path, index=False)
    resolution.to_csv(resolution_path, index=False)
    after_missing.to_csv(unresolved_path, index=False)
    _format_missing_report(before_missing).to_csv(missing_path, index=False)

    return {
        "before_missing": before_missing,
        "after_missing": after_missing,
        "candidates_path": candidates_path,
        "resolution_path": resolution_path,
        "unresolved_path": unresolved_path,
        "missing_path": missing_path,
    }


def _standardize_mapping(mappings):
    return {
        standardize_company_id(source): standardize_company_id(target)
        for source, target in mappings.items()
        if standardize_company_id(source) and standardize_company_id(target)
    }


def _closest_match(value, candidates):
    matches = get_close_matches(value, candidates, n=1, cutoff=0.0)
    if not matches:
        return None

    candidate = matches[0]
    return candidate, SequenceMatcher(None, value, candidate).ratio()


def _missing_lookup(missing_df):
    if missing_df.empty:
        return {}

    return {
        (row["company_id"], row["table_name"]): int(row["occurrences"])
        for _, row in missing_df.iterrows()
    }


def _format_missing_report(missing_df):
    if missing_df.empty:
        return pd.DataFrame(
            columns=["source_table", "missing_company_id", "occurrence_count"]
        )

    return missing_df.rename(
        columns={
            "table_name": "source_table",
            "company_id": "missing_company_id",
            "occurrences": "occurrence_count",
        }
    )[["source_table", "missing_company_id", "occurrence_count"]]

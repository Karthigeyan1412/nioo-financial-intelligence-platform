import sqlite3
from pathlib import Path

import pandas as pd


def calculate_free_cash_flow(operating_activity, investing_activity):
    return _to_number(operating_activity) + _to_number(investing_activity)


def calculate_cfo_quality_score(cfo_pat_pairs):
    ratios = []
    for cfo, pat in (cfo_pat_pairs or [])[:5]:
        if _is_zero(pat):
            return None
        ratios.append(_to_number(cfo) / _to_number(pat))

    if not ratios:
        return None

    return sum(ratios) / len(ratios)


def classify_cfo_quality(score):
    if score is None:
        return None

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def calculate_capex_intensity(investing_activity, sales):
    if _is_zero(sales):
        return None

    return (abs(_to_number(investing_activity)) / _to_number(sales)) * 100


def classify_capex_intensity(capex_intensity):
    if capex_intensity is None:
        return None

    if capex_intensity < 3:
        return "Asset Light"

    if capex_intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def calculate_fcf_conversion_rate(free_cash_flow, operating_profit):
    if _is_zero(operating_profit):
        return None

    return (_to_number(free_cash_flow) / _to_number(operating_profit)) * 100


def sign_label(value):
    value = _to_number(value)
    if value > 0:
        return "+"
    if value < 0:
        return "-"
    return "0"


def classify_capital_allocation_pattern(
    cfo,
    cfi,
    cff,
    cfo_quality_label=None,
):
    signs = (sign_label(cfo), sign_label(cfi), sign_label(cff))

    if signs == ("+", "-", "-") and cfo_quality_label == "High Quality":
        return "Shareholder Returns"

    pattern_map = {
        ("+", "-", "-"): "Reinvestor",
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }
    return pattern_map.get(signs, "Mixed")


def generate_capital_allocation_report(
    db_path="db/nifty100.db",
    output_path="output/capital_allocation.csv",
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        cashflow = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity
            FROM cashflow
            WHERE company_id IS NOT NULL
              AND year IS NOT NULL
            ORDER BY company_id, year
            """,
            connection,
        )

    rows = []
    for _, row in cashflow.iterrows():
        cfo = row["operating_activity"]
        cfi = row["investing_activity"]
        cff = row["financing_activity"]
        rows.append(
            {
                "company_id": row["company_id"],
                "year": int(row["year"]),
                "cfo_sign": sign_label(cfo),
                "cfi_sign": sign_label(cfi),
                "cff_sign": sign_label(cff),
                "pattern_label": classify_capital_allocation_pattern(
                    cfo,
                    cfi,
                    cff,
                ),
            }
        )

    report = pd.DataFrame(
        rows,
        columns=[
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ],
    )
    report.to_csv(output_path, index=False)
    return output_path


def _is_zero(value):
    return _to_number(value) == 0


def _to_number(value):
    if value is None or pd.isna(value):
        return 0

    return float(value)


if __name__ == "__main__":
    print(generate_capital_allocation_report())

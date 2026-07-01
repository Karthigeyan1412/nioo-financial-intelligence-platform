import logging


LOGGER = logging.getLogger(__name__)
FINANCIAL_SECTOR = "FINANCIALS"


def calculate_net_profit_margin(net_profit, sales):
    if _is_zero(sales):
        return None

    return _percentage(net_profit, sales)


def calculate_operating_profit_margin(
    operating_profit,
    sales,
    reported_opm_percentage=None,
    company_id=None,
):
    if _is_zero(sales):
        return None

    calculated_margin = _percentage(operating_profit, sales)
    if reported_opm_percentage is not None:
        difference = abs(calculated_margin - reported_opm_percentage)
        if difference > 1:
            LOGGER.warning(
                "Operating profit margin mismatch for %s: calculated %.2f, reported %.2f",
                company_id or "unknown company",
                calculated_margin,
                reported_opm_percentage,
            )

    return calculated_margin


def calculate_return_on_equity(net_profit, equity_capital, reserves):
    equity = _sum(equity_capital, reserves)
    if equity <= 0:
        return None

    return _percentage(net_profit, equity)


def calculate_return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings,
):
    capital_employed = _sum(equity_capital, reserves, borrowings)
    if capital_employed <= 0:
        return None

    return _percentage(ebit, capital_employed)


def is_roce_above_threshold(
    roce,
    broad_sector,
    normal_threshold=15,
    financial_sector_benchmark=None,
):
    if roce is None:
        return False

    threshold = normal_threshold
    if _is_financial_sector(broad_sector) and financial_sector_benchmark is not None:
        threshold = financial_sector_benchmark

    return roce >= threshold


def calculate_return_on_assets(net_profit, total_assets):
    if _is_zero(total_assets):
        return None

    return _percentage(net_profit, total_assets)


def calculate_debt_to_equity(borrowings, equity_capital, reserves):
    if _is_zero(borrowings):
        return 0

    equity = _sum(equity_capital, reserves)
    if equity <= 0:
        return None

    return borrowings / equity


def is_high_leverage(debt_to_equity, broad_sector):
    if debt_to_equity is None or _is_financial_sector(broad_sector):
        return False

    return debt_to_equity > 5


def calculate_interest_coverage_ratio(operating_profit, other_income, interest):
    if _is_zero(interest):
        return None

    return _sum(operating_profit, other_income) / interest


def get_icr_label(icr, interest):
    if icr is None and _is_zero(interest):
        return "Debt Free"

    return None


def has_icr_warning(icr):
    return icr is not None and icr < 1.5


def calculate_net_debt(borrowings, investments):
    return _to_number(borrowings) - _to_number(investments)


def calculate_asset_turnover(sales, total_assets):
    if _is_zero(total_assets):
        return None

    return _to_number(sales) / _to_number(total_assets)


def calculate_leverage_efficiency_metrics(
    sales,
    operating_profit,
    other_income,
    interest,
    borrowings,
    investments,
    equity_capital,
    reserves,
    total_assets,
    broad_sector,
):
    debt_to_equity = calculate_debt_to_equity(
        borrowings,
        equity_capital,
        reserves,
    )
    icr = calculate_interest_coverage_ratio(
        operating_profit,
        other_income,
        interest,
    )

    return {
        "debt_to_equity": debt_to_equity,
        "high_leverage_flag": is_high_leverage(debt_to_equity, broad_sector),
        "interest_coverage_ratio": icr,
        "icr_label": get_icr_label(icr, interest),
        "icr_warning_flag": has_icr_warning(icr),
        "net_debt": calculate_net_debt(borrowings, investments),
        "asset_turnover": calculate_asset_turnover(sales, total_assets),
    }


def _percentage(numerator, denominator):
    return (_to_number(numerator) / _to_number(denominator)) * 100


def _sum(*values):
    return sum(_to_number(value) for value in values)


def _is_zero(value):
    return _to_number(value) == 0


def _to_number(value):
    if value is None:
        return 0

    return float(value)


def _is_financial_sector(broad_sector):
    return str(broad_sector).strip().upper() == FINANCIAL_SECTOR

from dataclasses import dataclass


OK = "OK"
INSUFFICIENT = "INSUFFICIENT"
ZERO_BASE = "ZERO_BASE"
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class CAGRResult:
    value: float | None
    flag: str


def calculate_cagr(start_value, end_value, years):
    if start_value is None or end_value is None or years is None or years <= 0:
        return CAGRResult(None, INVALID_INPUT)

    start_value = float(start_value)
    end_value = float(end_value)

    if start_value == 0:
        return CAGRResult(None, ZERO_BASE)

    if start_value > 0 and end_value < 0:
        return CAGRResult(None, DECLINE_TO_LOSS)

    if start_value < 0 and end_value > 0:
        return CAGRResult(None, TURNAROUND)

    if start_value < 0 and end_value < 0:
        return CAGRResult(None, BOTH_NEGATIVE)

    return CAGRResult(
        (((end_value / start_value) ** (1 / years)) - 1) * 100,
        OK,
    )


def calculate_metric_cagrs(
    records,
    metric_name,
    output_prefix,
    periods=(3, 5, 10),
):
    by_year = _records_by_year(records, metric_name)
    output = {}

    if not by_year:
        for period in periods:
            output[f"{output_prefix}_cagr_{period}yr"] = None
            output[f"{output_prefix}_cagr_{period}yr_flag"] = INSUFFICIENT
        return output

    latest_year = max(by_year)
    for period in periods:
        value_key = f"{output_prefix}_cagr_{period}yr"
        flag_key = f"{output_prefix}_cagr_{period}yr_flag"
        start_year = latest_year - period

        if start_year not in by_year:
            output[value_key] = None
            output[flag_key] = INSUFFICIENT
            continue

        result = calculate_cagr(
            by_year[start_year],
            by_year[latest_year],
            period,
        )
        output[value_key] = result.value
        output[flag_key] = result.flag

    return output


def calculate_profitandloss_cagrs(records):
    output = {}
    output.update(calculate_metric_cagrs(records, "sales", "revenue"))
    output.update(calculate_metric_cagrs(records, "net_profit", "pat"))
    output.update(calculate_metric_cagrs(records, "eps", "eps"))
    return output


def _records_by_year(records, metric_name):
    by_year = {}
    for record in records or []:
        year = record.get("year")
        value = record.get(metric_name)
        if year is None or value is None:
            continue

        by_year[int(year)] = float(value)

    return by_year

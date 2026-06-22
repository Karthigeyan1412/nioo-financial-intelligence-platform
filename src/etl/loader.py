import pandas as pd


def normalize_column_name(column):
    """
    Convert source spreadsheet column names into database-friendly names.
    """

    column = str(column).strip().lower()
    column = column.replace("\n", " ")
    column = "_".join(column.split())
    return column


def normalize_year(year):
    """
    Convert different year formats into a standard year value.

    Examples:
        'Mar 2024' -> 2024
        'Dec 2012' -> 2012
        'FY2024' -> 2024
        '2024-25' -> 2024
        2024 -> 2024
    """

    if pd.isna(year):
        return None

    year = str(year).strip()

    digits = ''.join(
        char for char in year
        if char.isdigit()
    )

    if len(digits) >= 4:
        return int(digits[:4])

    return None


def normalize_ticker(ticker):
    """
    Standardize stock ticker symbols.

    Examples:
        tcs -> TCS
        tcs.ns -> TCS
        infy.ns -> INFY
    """

    if pd.isna(ticker):
        return None

    ticker = str(ticker).strip().upper()

    ticker = ticker.replace(".NS", "")

    return ticker


class ExcelLoader:

    def load_excel(self, file_path, header=1):
        """
        Load Excel file using the correct header row.
        """

        df = pd.read_excel(
            file_path,
            header=header
        )

        df.columns = [
            normalize_column_name(column)
            for column in df.columns
        ]

        df = df.dropna(how="all")

        # Normalize ticker column if present
        if "ticker" in df.columns:
            df["ticker"] = df["ticker"].apply(
                normalize_ticker
            )

        # Normalize company_id if it stores ticker symbols
        if "company_id" in df.columns:
            df["company_id"] = df["company_id"].astype(
                str).str.strip().str.upper()

        # Normalize year column
        if "year" in df.columns:
            df["year"] = df["year"].apply(
                normalize_year
            )

        return df

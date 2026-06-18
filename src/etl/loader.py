import pandas as pd


def normalize_year(year):

    if pd.isna(year):
        return None

    year = str(year).strip()

    digits = ''.join(char for char in year if char.isdigit())

    if len(digits) >= 4:
        return int(digits[:4])

    return None


def normalize_ticker(ticker):

    if pd.isna(ticker):
        return None

    ticker = str(ticker).strip().upper()

    ticker = ticker.replace(".NS", "")

    return ticker


class ExcelLoader:

    def load_excel(self, file_path):

        df = pd.read_excel(file_path)

        if "ticker" in df.columns:
            df["ticker"] = df["ticker"].apply(
                normalize_ticker
            )

        if "year" in df.columns:
            df["year"] = df["year"].apply(
                normalize_year
            )

        return df

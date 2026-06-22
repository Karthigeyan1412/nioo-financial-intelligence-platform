import pandas as pd

from src.etl.loader import normalize_column_name, normalize_ticker, normalize_year


ID_COLUMNS = {"company_id", "ticker"}
TEXT_COLUMNS = {
    "company_id",
    "ticker",
    "company_name",
    "company",
    "name",
    "sector",
    "industry",
    "peer_group",
    "pros",
    "cons",
}


def normalize_columns(df):
    clean = df.copy()
    clean.columns = [normalize_column_name(column) for column in clean.columns]
    if "id" in clean.columns and "company_id" not in clean.columns:
        clean = clean.rename(columns={"id": "company_id"})
    return clean


def normalize_dataframe(df):
    """
    Normalize a source DataFrame into a database-ready shape.
    """

    clean = normalize_columns(df)
    clean = clean.dropna(how="all")

    if "ticker" in clean.columns:
        clean["ticker"] = clean["ticker"].apply(normalize_ticker)

    if "company_id" in clean.columns:
        clean["company_id"] = (
            clean["company_id"]
            .astype("string")
            .str.strip()
            .str.upper()
            .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
        )

    if "year" in clean.columns:
        clean["year"] = clean["year"].apply(normalize_year)

    for column in clean.columns:
        if column in ID_COLUMNS or column == "year":
            continue

        if column in TEXT_COLUMNS:
            clean[column] = clean[column].apply(_clean_text)
            continue

        if clean[column].dtype == "object":
            clean[column] = clean[column].apply(_clean_text)
            numeric = pd.to_numeric(clean[column], errors="coerce")
            if numeric.notna().sum() == clean[column].notna().sum():
                clean[column] = numeric

    return clean


def normalize_dataset(name, df):
    """
    Named entry point used by the pipeline.
    """

    return normalize_dataframe(df)


def _clean_text(value):
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text or text.upper() in {"NAN", "NONE"}:
        return None

    return text

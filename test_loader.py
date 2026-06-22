from src.etl.loader import ExcelLoader

loader = ExcelLoader()

df = loader.load_excel(
    "data/main/profitandloss.xlsx"
)

print(df.head())
print(df.columns.tolist())

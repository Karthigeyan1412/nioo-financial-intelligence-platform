import pandas as pd

files = [
    "companies.xlsx",
    "balancesheet.xlsx",
    "profitandloss.xlsx"
]

for file in files:
    print(f"\n{'='*50}")
    print(file)
    print('='*50)

    df = pd.read_excel(
        f"data/main/{file}",
        header=None
    )

    print(df.head(15))

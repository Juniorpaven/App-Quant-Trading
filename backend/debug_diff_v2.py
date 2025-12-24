
from vnstock import Finance
import pandas as pd

def print_ratios(df, label):
    if df is None or df.empty:
        print(f"No data for {label}")
        return

    # Flatten columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [' '.join(col).strip() for col in df.columns.values]
    
    # Find P/E and ROE columns
    pe_col = next((c for c in df.columns if 'price to earning' in c.lower() or 'p/e' in c.lower()), None)
    roe_col = next((c for c in df.columns if 'roe' in c.lower()), None)
    
    print(f"--- {label} ---")
    print(f"Columns Found: PE={pe_col}, ROE={roe_col}")
    if pe_col and roe_col:
        print(df[['Meta Năm', 'Meta Kỳ', pe_col, roe_col]].head(3))
    else:
        print(df.head(1))

try:
    fin = Finance(symbol='HPG', source='VCI')
    print_ratios(fin.ratio(period='quarterly', lang='vi'), "QUARTERLY")
    print_ratios(fin.ratio(period='yearly', lang='vi'), "YEARLY")
except Exception as e:
    print(e)

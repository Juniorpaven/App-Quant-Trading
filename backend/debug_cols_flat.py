
from vnstock import Finance
import pandas as pd

try:
    fin = Finance(symbol='HPG', source='VCI')
    df = fin.ratio(period='quarterly', lang='vi')
    
    # Flatten columns
    if isinstance(df.columns, pd.MultiIndex):
        # Join levels with space or underscore
        df.columns = ['_'.join(col).strip() for col in df.columns.values]
    
    print("Flat Columns:", df.columns.tolist())
    print("First row dict:", df.iloc[0].to_dict())

except Exception as e:
    print(e)

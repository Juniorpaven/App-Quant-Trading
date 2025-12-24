
from vnstock import Finance
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

try:
    fin = Finance(symbol='HPG', source='VCI')
    
    print("--- QUARTERLY DATA (Latest 3) ---")
    df_q = fin.ratio(period='quarterly', lang='vi')
    if df_q is not None:
        print(df_q.head(3))
        
    print("\n--- YEARLY DATA (Latest 3) ---")
    df_y = fin.ratio(period='yearly', lang='vi')
    if df_y is not None:
        print(df_y.head(3))

except Exception as e:
    print(e)

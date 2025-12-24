
from vnstock import Finance
try:
    fin = Finance(symbol='HPG', source='VCI')
    print("Fetching English data...")
    df = fin.ratio(period='quarterly', lang='en')
    print("Columns (English):", df.columns)
    print("First row:", df.iloc[0].to_dict())
    
    print("\nFetching Vietnamese data...")
    df_vi = fin.ratio(period='quarterly', lang='vi')
    print("Columns (Vietnamese):", df_vi.columns)
    
except Exception as e:
    print(e)

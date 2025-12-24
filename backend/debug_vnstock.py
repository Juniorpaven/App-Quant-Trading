
try:
    from vnstock import stock_historical_data
    from datetime import datetime
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = "2023-01-01"
    
    print(f"Fetching HPG from {start_date} to {end_date}")
    df = stock_historical_data("HPG", start_date, end_date, "1D", "stock")
    
    if df is not None and not df.empty:
        print("Columns:", df.columns.tolist())
        print(df.tail())
    else:
        print("Empty dataframe from vnstock")

except Exception as e:
    print(f"Error: {e}")

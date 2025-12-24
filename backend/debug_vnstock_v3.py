
try:
    from vnstock import Vnstock
    print("Vnstock imported")
    
    # Method 1
    try:
        print("Attempting Method 1: Vnstock().stock().quote.history()")
        stock = Vnstock().stock(symbol='HPG', source='VCI')
        df = stock.quote.history(start='2024-01-01', end='2024-12-01')
        print("Success!")
        print(df.head())
        print(df.columns)
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2 (Direct function from old version? No)
    
except Exception as e:
    print(f"Import failed: {e}")

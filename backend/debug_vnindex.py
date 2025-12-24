
from vnstock import Vnstock
try:
    print("Testing VNINDEX with VCI...")
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    df = stock.quote.history(symbol='VNINDEX', start='2024-12-01', end='2024-12-25')
    if df is not None and not df.empty:
        print("Success with VNINDEX")
        print(df.tail(2))
    else:
        print("Failed with VNINDEX")

    print("\nTesting ^VNINDEX just in case...")
    stock2 = Vnstock().stock(symbol='^VNINDEX', source='VCI')
    df2 = stock2.quote.history(symbol='^VNINDEX', start='2024-12-01', end='2024-12-25')
    if df2 is not None and not df2.empty:
        print("Success with ^VNINDEX")
    else:
        print("Failed with ^VNINDEX")

except Exception as e:
    print(f"Error: {e}")

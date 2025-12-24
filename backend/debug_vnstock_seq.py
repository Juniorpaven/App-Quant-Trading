
from vnstock import Vnstock
import time

tickers = ["HPG", "VNM", "FPT"]
print("Testing sequential fetch with vnstock...")

for t in tickers:
    try:
        print(f"Fetching {t}...")
        stock = Vnstock().stock(symbol=t, source='VCI')
        df = stock.quote.history(symbol=t, start='2024-12-01', end='2024-12-25')
        if df is not None and not df.empty:
            print(f"Success {t}: {len(df)} rows")
        else:
            print(f"Empty {t}")
        time.sleep(1) # Polite delay
    except Exception as e:
        print(f"Error {t}: {e}")

print("Testing VNINDEX...")
try:
    stock = Vnstock().stock(symbol='VNINDEX', source='VCI')
    df = stock.quote.history(symbol='VNINDEX', start='2024-12-01', end='2024-12-25')
    if df is not None and not df.empty:
        print(f"Success VNINDEX: {len(df)} rows")
    else:
        print("Empty VNINDEX")
except Exception as e:
    print(f"Error VNINDEX: {e}")

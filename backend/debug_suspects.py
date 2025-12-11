
import yfinance as yf
import pandas as pd
import time

def check_one_by_one():
    tickers = ["MSB.VN", "SSB.VN", "EIB.VN", "BAB.VN", "NAB.VN", "OCB.VN"]
    print("Checking suspects...")
    
    for t in tickers:
        print(f"--- Checking {t} ---")
        d = yf.download(t, period="1mo", progress=False, auto_adjust=False)
        if d.empty:
            print(f"RESULT: {t} is EMPTY")
        else:
            print(f"RESULT: {t} has {len(d)} rows")
        print("")
        time.sleep(1)

if __name__ == "__main__":
    check_one_by_one()


import yfinance as yf
from datetime import datetime
import pandas as pd

def test_fetch():
    print("Testing 5y fetch using period='5y'...")
    data = yf.download("BTC-USD", period="5y", progress=False)
    if isinstance(data, pd.DataFrame):
        print(f"Shape: {data.shape}")
        if not data.empty:
            print(f"Start: {data.index[0]}")
            print(f"End: {data.index[-1]}")
            days = (data.index[-1] - data.index[0]).days
            print(f"Total days: {days}")
            if days > 1000:
                print("SUCCESS: > 3 years acquired")
            else:
                print("FAIL: < 3 years acquired")
    else:
        print("Data is not DataFrame")

if __name__ == "__main__":
    test_fetch()

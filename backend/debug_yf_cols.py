
import yfinance as yf
import pandas as pd
import time

tickers = ["ACB.VN", "BCM.VN", "FPT.VN"] # Test small set

print(f"Testing Yahoo Batch Download DEBUG...")
try:
    # Remove ['Adj Close'] to see full structure first
    data = yf.download(tickers, period="1y", progress=True)
    print("Full DataFrame Columns:", data.columns)
    
    if 'Adj Close' in data:
         print("Adj Close found directly.")
    elif 'Close' in data:
         print("Close found (Auto adjusted?)")
    else:
         print("Neither found directly.")
         
except Exception as e:
    print(f"ERROR: {e}")

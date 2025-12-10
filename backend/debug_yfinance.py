
import yfinance as yf
import pandas as pd

try:
    print("Testing yfinance download...")
    tickers = ["AAPL", "MSFT", "GOOG"]
    data = yf.download(tickers, period="1mo")
    print("Download finished.")
    print("Columns:", data.columns)
    print("Shape:", data.shape)
    print("Head:\n", data.head())
    
    if hasattr(data.columns, 'levels'):
        print("Levels:", data.columns.levels)
        if 'Adj Close' in data.columns.get_level_values(0):
            print("Found Adj Close at level 0")
            print(data['Adj Close'].head())
        elif 'Close' in data.columns.get_level_values(0):
            print("Found Close at level 0")
    
except Exception as e:
    print("Error:", e)

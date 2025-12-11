
import yfinance as yf
import pandas as pd

def test_ticker(ticker):
    print(f"Testing ticker: {ticker}")
    try:
        data = yf.download(ticker, period="1y", progress=False)
        if data.empty:
            print("Data is empty!")
        else:
            print("Data fetched successfully:")
            print(data.head())
            print("Adj Close:")
            # Handle multi-index columns if necessary, though single ticker usually simple
            try:
                print(data['Adj Close'].head())
            except KeyError:
                print("'Adj Close' not found. Columns:", data.columns)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ticker("HPG.VN")


import yfinance as yf
import pandas as pd

def test_tickers():
    tickers = ["VCB.VN", "SSI-VN"] # User input from screenshot
    print(f"Testing tickers: {tickers}")
    
    # Simulate get_data logic
    try:
        data = yf.download(tickers, period="1y", progress=False, auto_adjust=False)['Adj Close']
        
        print("\nRaw Data Head:")
        print(data.head())
        print("\nRaw Data Describe:")
        print(data.describe())
        
        # Check for NaNs
        print("\nNaN counts per column:")
        print(data.isna().sum())
        
        # Simulate dropna
        data_dropped = data.dropna()
        print(f"\nData shape after dropna(): {data_dropped.shape}")
        
        if data_dropped.empty:
            print("RESULT: Data is empty after dropna()! This causes the error.")
        else:
            print("RESULT: Data is NOT empty.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tickers()

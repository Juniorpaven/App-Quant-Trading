
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- MOCK DATA CACHE ---
DATA_CACHE = {}

# --- COPIED FROM main.py ---
def get_data(tickers, period="1y"):
    tickers = [t.strip().upper() for t in tickers]
    key = tuple(sorted(tickers))
    
    print(f"Fetching: {tickers}")
    data = yf.download(tickers, period=period, progress=False, auto_adjust=False)['Adj Close']
    
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    
    # 1. Drop Columns (Tickers) that have NO data
    data = data.dropna(axis=1, how='all')
    
    if data.empty:
         return data

    # 2. Forward fill and dropna
    data = data.ffill().dropna()
    print(f"Data shape after cleaning: {data.shape}")
    print(data.head())
    print(data.tail())
    return data

def calculate_ops_eg(data, eta=0.05):
    print("Starting OPS Calculation...")
    try:
        returns = data.pct_change().dropna().values 
        T, N = returns.shape 
        print(f"Returns shape: T={T}, N={N}")
        
        if T == 0: 
            print("Error: T=0")
            return {}

        weights = np.ones(N) / N
        
        for t in range(T):
            portfolio_ret = np.dot(weights, returns[t])
            if portfolio_ret == 0: portfolio_ret = 1e-10
                
            exponent = eta * returns[t] / portfolio_ret
            # Check for overflow/NaN
            if np.any(np.isnan(exponent)) or np.any(np.isinf(exponent)):
                print(f"Warning: NaN/Inf detected at step {t}")
            
            weights = weights * np.exp(exponent)
            weights /= np.sum(weights)
            
        result = dict(zip(data.columns, np.round(weights, 4)))
        print("OPS Result:", result)
        return result
    except Exception as e:
        print(f"OPS CRASHED: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    tickers = ["MSB.VN", "CTG.VN"]
    try:
        data = get_data(tickers)
        if data.empty:
             print("Data is empty, cannot run OPS")
        else:
            calculate_ops_eg(data)
    except Exception as e:
        print(f"Top level error: {e}")

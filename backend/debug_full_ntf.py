
import yfinance as yf
import pandas as pd

def debug_full_ntf():
    tickers_input = "VCB.VN, BID.VN, CTG.VN, TCB.VN, VPB.VN, MBB.VN, ACB.VN, STB.VN, HDB.VN, VIB.VN, SHB.VN, LPB.VN, TPB.VN, OCB.VN, MSB.VN, SSB.VN, EIB.VN, BAB.VN, NAB.VN"
    tickers = [t.strip() for t in tickers_input.split(",")]
    
    print(f"Input count: {len(tickers)}")
    
    # Simulate get_data
    # 1. Download
    print("Downloading...")
    # Using group_by='ticker' to be safe with multi-index
    raw = yf.download(tickers, period="1y", progress=False, group_by='ticker', auto_adjust=False)
    
    data = pd.DataFrame()
    for t in tickers:
        if t in raw.columns.levels[0]:
            try:
                # Try Adj Close, then Close
                if 'Adj Close' in raw[t]:
                    data[t] = raw[t]['Adj Close']
                elif 'Close' in raw[t]:
                    data[t] = raw[t]['Close']
            except:
                pass
                
    print(f"Columns after download: {len(data.columns)}")
    print(f"Missing after download: {list(set(tickers) - set(data.columns))}")
    
    # 2. Backend Cleaning Logic
    data = data.dropna(axis=1, how='all')
    print(f"Columns after dropna(axis=1): {len(data.columns)}")
    
    data = data.ffill().dropna()
    print(f"Columns after ffill/dropna: {len(data.columns)}")
    print(f"Rows: {len(data)}")
    
    # 3. NTF Logic
    returns = data.pct_change().dropna()
    momentum = returns.iloc[-20:].mean() * 252
    scores = momentum.to_dict()
    
    print(f"Final Score Count: {len(scores)}")
    print("Final Keys:", list(scores.keys()))

if __name__ == "__main__":
    debug_full_ntf()

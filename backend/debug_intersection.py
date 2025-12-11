
import yfinance as yf
import pandas as pd

def debug_intersection():
    tickers_str = "VCB.VN, BID.VN, CTG.VN, TCB.VN, VPB.VN, MBB.VN, ACB.VN, STB.VN, HDB.VN, VIB.VN, SHB.VN, LPB.VN, TPB.VN, OCB.VN, MSB.VN, SSB.VN, EIB.VN, BAB.VN, NAB.VN"
    tickers = [t.strip() for t in tickers_str.split(",")]
    
    print("Downloading all tickers...")
    data = yf.download(tickers, period="1y", progress=False, group_by='ticker', auto_adjust=False)
    
    # Extract Adj Close manually to avoid multi-index confusion
    adj_close = pd.DataFrame()
    for t in tickers:
        try:
            if t in data.columns.levels[0]:
                col = data[t]['Adj Close']
                adj_close[t] = col
            else:
                print(f"MISSING RAW: {t}")
        except Exception as e:
            print(f"Error extracting {t}: {e}")
            
    print(f"\nShape after extract: {adj_close.shape}")
    print("Columns present:", adj_close.columns.tolist())
    
    # 1. Check Empty Columns
    empty_cols = adj_close.columns[adj_close.isna().all()].tolist()
    print(f"Empty Columns (No Data): {empty_cols}")
    
    # 2. Check Valid Data Start Dates
    print("\nStart Dates:")
    for c in adj_close.columns:
        valid_idx = adj_close[c].first_valid_index()
        print(f"{c}: {valid_idx}")

    # 3. Simulate Backend Cleaning
    cleaned = adj_close.dropna(axis=1, how='all')
    print(f"\nAfter dropna(axis=1): {cleaned.shape} (Columns: {cleaned.columns.tolist()})")
    
    final = cleaned.ffill().dropna()
    print(f"After ffill().dropna() (Backend Logic): {final.shape}")
    print(f"Final Columns: {final.columns.tolist()}")

    # Identify dropped columns
    dropped_cols = set(tickers) - set(final.columns)
    print(f"\nLOST TICKERS: {dropped_cols}")

if __name__ == "__main__":
    debug_intersection()


import yfinance as yf
import pandas as pd

def check_tickers():
    tickers_str = "VCB.VN, BID.VN, CTG.VN, TCB.VN, VPB.VN, MBB.VN, ACB.VN, STB.VN, HDB.VN, VIB.VN, SHB.VN, LPB.VN, TPB.VN, OCB.VN, MSB.VN, SSB.VN, EIB.VN, BAB.VN, NAB.VN"
    tickers = [t.strip() for t in tickers_str.split(",")]
    
    print(f"Checking {len(tickers)} tickers...")
    
    # Download individually to see which one fails specifically
    print(f"{'Ticker':<10} | {'Status':<10} | {'Rows':<5} | {'First Date'}")
    print("-" * 45)
    
    missing = []
    
    for t in tickers:
        try:
            # Use same settings as backend
            data = yf.download(t, period="1y", progress=False, auto_adjust=False)
            
            if data.empty:
                print(f"{t:<10} | {'EMPTY':<10} | 0     | N/A")
                missing.append(t)
            else:
                # Check Adj Close existence
                if 'Adj Close' in data.columns:
                     d = data['Adj Close']
                elif 'Close' in data.columns:
                     d = data['Close']
                else:
                     d = pd.Series()
                     
                if isinstance(d, pd.DataFrame):
                    # Handle multi-index if yf returns it
                    d = d.iloc[:, 0]
                
                # Check actual valid rows
                valid_count = d.dropna().shape[0]
                first_date = d.dropna().index[0].date() if valid_count > 0 else "N/A"
                
                status = "OK" if valid_count > 20 else "FEW DATA"
                print(f"{t:<10} | {status:<10} | {valid_count:<5} | {first_date}")
                
                if valid_count == 0:
                    missing.append(t)
                    
        except Exception as e:
            print(f"{t:<10} | {'ERROR':<10} | {str(e)}")
            missing.append(t)
            
    print("-" * 45)
    print(f"Missing/Empty Tickers: {missing}")

if __name__ == "__main__":
    check_tickers()

import yfinance as yf
import pandas as pd
from datetime import datetime

VN30_LIST = [
    "ACB.VN", "BCM.VN", "BID.VN", "BVH.VN", "CTG.VN", "FPT.VN", "GAS.VN", "GVR.VN",
    "HDB.VN", "HPG.VN", "MBB.VN", "MSN.VN", "MWG.VN", "PLX.VN", "POW.VN", "SAB.VN",
    "SHB.VN", "SSB.VN", "SSI.VN", "STB.VN", "TCB.VN", "TPB.VN", "VCB.VN", "VHM.VN",
    "VIB.VN", "VIC.VN", "VJC.VN", "VNM.VN", "VPB.VN", "VRE.VN"
]

def check_yahoo_health():
    print("--- START DEBUG YFINANCE ---")
    full_list = VN30_LIST + ["^VNINDEX"]
    print(f"Target Tickers: {len(full_list)} symbols")
    
    start_time = datetime.now()
    
    # Try fetching 6mo like the hotfix
    print("\nAttempt 1: Fetching period='6mo'...")
    try:
        data = yf.download(full_list, period="6mo", progress=True, auto_adjust=False)['Adj Close']
        
        duration = (datetime.now() - start_time).total_seconds()
        print(f"Download took: {duration:.2f} seconds")
        
        if data.empty:
            print("❌ RESULT: DATA EMPTY! (Yahoo blocked or all failed)")
        else:
            print(f"✅ RESULT: SUCCESS! Shape: {data.shape}")
            print(f"Rows (Days): {len(data)}")
            
            # Check length constraint
            if len(data) < 60:
                print(f"⚠️ WARNING: Data length {len(data)} < 60! Validation will fail.")
                
            # Check individual columns
            missing = [t for t in full_list if t not in data.columns]
            if missing:
                print(f"⚠️ MISSING SYMBOLS: {missing}")
            else:
                print("✅ All symbols present.")
                
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

if __name__ == "__main__":
    check_yahoo_health()

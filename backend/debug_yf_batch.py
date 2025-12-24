
import yfinance as yf
import pandas as pd
import time

tickers = ["ACB.VN", "BCM.VN", "BID.VN", "BVH.VN", "CTG.VN", "FPT.VN", "GAS.VN", "GVR.VN", "HDB.VN", "HPG.VN", "MBB.VN", "MSN.VN", "MWG.VN", "PLX.VN", "POW.VN", "SAB.VN", "SHB.VN", "SSB.VN", "SSI.VN", "STB.VN", "TCB.VN", "TPB.VN", "VCB.VN", "VHM.VN", "VIB.VN", "VIC.VN", "VJC.VN", "VNM.VN", "VPB.VN", "VRE.VN"]

print(f"Testing Yahoo Batch Download for {len(tickers)} tickers...")
start = time.time()
try:
    data = yf.download(tickers, period="1y", progress=True)['Adj Close']
    
    # Check emptiness
    if data is None or data.empty:
        print("RESULT: Empty DataFrame returned.")
    else:
        print(f"RESULT: Success. Shape: {data.shape}")
        print("Sample Data:")
        print(data.iloc[-1].head())
        
        # Check missing cols
        missing = [t for t in tickers if t not in data.columns]
        if missing:
            print(f"Missing columns: {missing}")
        else:
            print("All tickers present.")

except Exception as e:
    print(f"ERROR: {e}")

end = time.time()
print(f"Time taken: {end - start:.2f} seconds")

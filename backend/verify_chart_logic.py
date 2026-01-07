
import sys
import os
import pandas as pd
import json
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.main import get_ohlcv_smart, plot_candlestick_with_vp
    
    print("--- Testing get_ohlcv_smart('HPG') ---")
    df = get_ohlcv_smart("HPG.VN")
    
    if df.empty:
        print("RESULT: DataFrame is EMPTY")
    else:
        print(f"RESULT: DataFrame has {len(df)} rows")
        print(df.head(3))
        print("Columns:", df.columns.tolist())
        
        print("\n--- Testing plot_candlestick_with_vp ---")
        try:
            fig = plot_candlestick_with_vp(df, "HPG")
            json_out = json.loads(fig.to_json())
            print("RESULT: Plot GL JSON generated successfully")
            print("Keys:", json_out.keys())
            if 'data' in json_out:
                print(f"Data traces: {len(json_out['data'])}")
        except Exception as e:
            print(f"RESULT: Plot Logic Failed: {e}")

except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback to direct check if import fails due to path issues
    print("Could not import main. Please check path.")
except Exception as e:
    print(f"General Error: {e}")

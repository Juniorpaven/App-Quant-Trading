
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import sys
import os
import yfinance as yf
from datetime import datetime, timedelta

# Create a way to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core_engine.ntf_engine import calculate_dynamic_network_momentum
from core_engine.ops_engine import exponential_gradient_update, apply_group_sparsity

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://quant-frontend.vercel.app",
    "https://app-quant-trading.onrender.com",
    "https://app-quant-trading-cvpbihqnv-juniorpavens-projects.vercel.app", # URL cụ thể
    "https://app-quant-trading-gamma.vercel.app", # URL ngắn gọn thường có
    "https://app-quant-trading.vercel.app" # URL gốc (dự đoán)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CACHING (Zero-Cost Strategy) ---
DATA_CACHE = {}
CACHE_EXPIRY_TIME = timedelta(hours=4)

def get_cached_data(tickers: List[str], period="1y"):
    cache_key = tuple(sorted(tickers))
    if cache_key in DATA_CACHE:
        timestamp, data = DATA_CACHE[cache_key]
        if datetime.now() - timestamp < CACHE_EXPIRY_TIME:
            print(f"Adding from cache: {tickers}")
            return data
    
    print(f"Fetching fresh data for: {tickers}")
    try:
        # Request data
        # auto_adjust=True means 'Close' is already adjusted. 
        data = yf.download(tickers, period=period, auto_adjust=False)
        print(f"Downloaded shape: {data.shape}")
        
        if data.empty:
             raise Exception("yfinance returned empty data")

        # Handle MultiIndex
        # Expected: Level 0 = Price Type (Adj Close, Close), Level 1 = Ticker
        price_data = None
        
        if isinstance(data.columns, pd.MultiIndex):
            # Check for Adj Close
            if 'Adj Close' in data.columns.get_level_values(0):
                 price_data = data['Adj Close']
            elif 'Close' in data.columns.get_level_values(0):
                 price_data = data['Close']
            else:
                 # Fallback: take the first level 0 key?
                 print(f"Unrecognized columns levels: {data.columns.levels}")
                 # Try to just return data if it looks like price
                 price_data = data
        else:
            # Flat columns. Check if one of them is 'Adj Close' or 'Close'
            if 'Adj Close' in data.columns:
                price_data = data['Adj Close']
            elif 'Close' in data.columns:
                price_data = data['Close']
            else:
                 # Ensure we have numeric data
                 price_data = data

        # Check if price_data is Series (single ticker) -> convert to DF
        if isinstance(price_data, pd.Series):
             price_data = price_data.to_frame(name=tickers[0])
             
        # Filter for only requested tickers if extra columns exist
        # (Rare, but good safety)
        # Verify columns overlap with requested tickers
        # common_tickers = list(set(price_data.columns) & set(tickers))
        # if common_tickers:
        #    price_data = price_data[common_tickers]
        
        # Fill NA forward then backward
        price_data = price_data.ffill().bfill()
        
        print(f"Processed Price Data Shape: {price_data.shape}")
        print(f"Processed Price Data Head: \n{price_data.head()}")

        DATA_CACHE[cache_key] = (datetime.now(), price_data)
        return price_data
    except Exception as e:
        print(f"Error fetching yfinance data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Data Fetch Error: {str(e)}")

# --- MODELS ---

class NTFRequest(BaseModel):
    prices: Dict[str, List[float]] 
    lookback_window: int = 10
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prices": {
                        "BTC": [100, 101, 102, 101, 103, 105, 104, 106, 108, 107],
                        "ETH": [200, 202, 201, 203, 205, 204, 206, 208, 209, 210]
                    },
                    "lookback_window": 5
                }
            ]
        }
    }

class NTFTickerRequest(BaseModel):
    tickers: List[str]
    lookback_window: int = 20

class OPSRequest(BaseModel):
    current_weights: List[float]
    bi_return_vector: List[float]
    learning_rate: float = 0.5
    group_mapping: Optional[Dict[int, int]] = None
    alpha: float = 0.0
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_weights": [0.5, 0.5],
                    "bi_return_vector": [1.02, 0.98],
                    "learning_rate": 0.5
                }
            ]
        }
    }

@app.get("/")
def read_root():
    return {"status": "Quant Trading Backend is Running (Zero-Cost Mode)", "modules": ["NTF", "OPS", "YFinance"]}

@app.post("/api/ntf/momentum")
def get_ntf_momentum(request: NTFRequest):
    """Calculates momentum using manually provided price data."""
    try:
        df_prices = pd.DataFrame(request.prices)
        df_returns = df_prices.pct_change().dropna()
        if df_returns.empty:
            raise HTTPException(status_code=400, detail="Not enough data")
        
        momentum = calculate_dynamic_network_momentum(df_returns, request.lookback_window)
        results = {k: float(v) for k, v in momentum.items()}
        return {"momentum": results, "source": "manual_input"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-ntf-engine")
def run_ntf_analysis(request: NTFTickerRequest):
    """Fetches real data from yfinance and calculates momentum."""
    if not request.tickers:
        raise HTTPException(status_code=400, detail="Tickers list is empty")
        
    try:
        # Get data
        df_prices = get_cached_data(request.tickers)
        
        # Calculate Returns
        df_returns = df_prices.pct_change().dropna()
        
        # Ensure enough data
        if len(df_returns) < request.lookback_window:
             raise HTTPException(status_code=400, detail=f"Not enough historical data for analysis. Got {len(df_returns)} rows.")

        # Use the powerful Engine
        momentum = calculate_dynamic_network_momentum(df_returns, request.lookback_window)
        
        results = {k: float(v) for k, v in momentum.items()}
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "momentum": results, 
            "data_source": "yfinance (cached)"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ops/update")
def update_portfolio(request: OPSRequest):
    try:
        current_w = np.array(request.current_weights)
        ret_vec = np.array(request.bi_return_vector)
        if len(current_w) != len(ret_vec):
             raise HTTPException(status_code=400, detail="Dimension mismatch")

        new_w = exponential_gradient_update(
            current_w, 
            ret_vec, 
            request.learning_rate,
            group_mapping=request.group_mapping,
            alpha=request.alpha
        )
        return {"new_weights": new_w.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

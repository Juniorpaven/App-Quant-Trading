
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = FastAPI()

# Cấu hình CORS (Giữ nguyên URL Vercel của bạn)
origins = [
    "http://localhost:5173",
    "https://app-quant-trading.vercel.app", # Đảm bảo đúng URL của bạn
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CACHING & DATA UTILS ---
DATA_CACHE = {}

def get_data(tickers, period="1y"): # Lấy 1 năm để OPS học tốt hơn
    tickers = [t.strip().upper() for t in tickers]
    key = tuple(sorted(tickers))
    
    if key in DATA_CACHE and (datetime.now() - DATA_CACHE[key][0] < timedelta(hours=4)):
        return DATA_CACHE[key][1]
        
    print(f"Fetching: {tickers}")
    data = yf.download(tickers, period=period, progress=False, auto_adjust=False)['Adj Close']
    
    # Nếu chỉ có 1 ticker, yfinance trả về Series, cần convert sang DataFrame
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    
    # 1. Drop Columns (Tickers) that have NO data (failed download)
    data = data.dropna(axis=1, how='all')
    
    if data.empty:
         # Nếu drop hết thì return empty distinct
         return data

    # 2. Drop Rows (Dates) that have NaN (ensure alignment for remaining tickers)
    # Tuy nhiên, nếu dữ liệu các mã lệch nhau quá nhiều (VD: BTC chạy 24/7, Stock chạy T2-T6)
    # Dropna sẽ làm mất hết dữ liệu BTC vào T7, CN. 
    # Tốt nhất là forward fill trước khi dropna
    data = data.ffill().dropna()
    
    DATA_CACHE[key] = (datetime.now(), data)
    return data

# --- ALGORITHMS ---

# 1. NTF Algorithm (Giữ nguyên logic cũ nhưng dynamic ticker)
def calculate_ntf(data, lookback=20):
    returns = data.pct_change().dropna()
    if len(returns) < lookback:
        return {"error": "Not enough data"}
    
    momentum = returns.iloc[-lookback:].mean() * 252
    scores = momentum.to_dict()
    # Làm tròn số
    return {k: round(v, 4) for k, v in scores.items()}

# 2. OPS Algorithm: Exponential Gradient (EG)
def calculate_ops_eg(data, eta=0.05):
    """
    Thuật toán Exponential Gradient để tìm tỷ trọng tối ưu.
    Input: DataFrame giá đóng cửa.
    Output: Tỷ trọng (Weights) gợi ý cho ngày tiếp theo.
    """
    returns = data.pct_change().dropna().values # Chuyển sang numpy array
    T, N = returns.shape # T: số ngày, N: số tài sản
    
    if T == 0: return {}

    # Khởi tạo tỷ trọng đều nhau: [1/N, 1/N, ...]
    weights = np.ones(N) / N
    
    # Chạy mô phỏng Online Learning qua từng ngày quá khứ
    for t in range(T):
        # Lợi nhuận danh mục tại t: dot product của weights và returns
        portfolio_ret = np.dot(weights, returns[t])
        
        # Cập nhật weights theo công thức EG:
        # w_new = w_old * exp(eta * return_asset / portfolio_return)
        # Tránh chia cho 0 hoặc số quá nhỏ
        if portfolio_ret == 0: portfolio_ret = 1e-10
            
        exponent = eta * returns[t] / portfolio_ret
        weights = weights * np.exp(exponent)
        
        # Chuẩn hóa lại để tổng weights = 1 (Simplex projection)
        weights /= np.sum(weights)
        
    # Gán nhãn Ticker cho kết quả cuối cùng
    result = dict(zip(data.columns, np.round(weights, 4)))
    return result

# --- API MODELS ---
class NTFRequest(BaseModel):
    tickers: str # Dạng chuỗi: "BTC-USD, ETH-USD"
    lookback: int = 20

class OPSRequest(BaseModel):
    tickers: str
    eta: float = 0.05 # Learning rate

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "Backend is running (Zero-Cost Mode)"}

@app.post("/api/run-ntf")
def run_ntf_endpoint(req: NTFRequest):
    ticker_list = [t.strip() for t in req.tickers.split(",")]
    try:
        data = get_data(ticker_list)
        results = calculate_ntf(data, req.lookback)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-ops")
def run_ops_endpoint(req: OPSRequest):
    ticker_list = [t.strip() for t in req.tickers.split(",")]
    if len(ticker_list) < 2:
         raise HTTPException(status_code=400, detail="OPS cần ít nhất 2 tài sản để phân bổ.")
    try:
        data = get_data(ticker_list)
        weights = calculate_ops_eg(data, req.eta)
        return {"status": "success", "weights": weights, "algo": "Exponential Gradient"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

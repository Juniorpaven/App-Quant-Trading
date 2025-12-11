
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
        if abs(portfolio_ret) < 1e-8: 
            portfolio_ret = 1e-8
            
        exponent = eta * returns[t] / portfolio_ret
        
        # FIX: Clip exponent để tránh Overflow (e^709 -> inf)
        exponent = np.clip(exponent, -30, 30)
        
        weights = weights * np.exp(exponent)
        
        # FIX: Handle potential Inf/NaN in weights
        if np.any(np.isinf(weights)) or np.any(np.isnan(weights)):
             weights = np.ones(N) / N # Reset if math error
             
        # Chuẩn hóa lại để tổng weights = 1 (Simplex projection)
        weights /= np.sum(weights)
        
    # Gán nhãn Ticker cho kết quả cuối cùng
    # Convert numpy types to native float for JSON serialization safety
    final_weights = [float(w) if not np.isnan(w) else 0.0 for w in weights]
    result = dict(zip(data.columns, [round(w, 4) for w in final_weights]))
    return result

# --- BACKTESTING ENGINE ---

def apply_max_weight_constraint(weights, max_weight):
    # If max_weight >= 1.0, it does nothing
    if max_weight >= 1.0 - 1e-5:
        return weights
    
    # Simple projection: clip and re-normalize, iterate a few times
    for _ in range(5): # 5 iterations usually enough for simple constraints
        weights = np.minimum(weights, max_weight)
        if np.sum(weights) == 0: return np.ones(len(weights)) / len(weights)
        weights /= np.sum(weights)
        if np.all(weights <= max_weight + 1e-5):
            break
            
    return weights

def run_backtest_simulation(data, eta=0.05, max_weight=1.0):
    """
    Giả lập hiệu suất đầu tư theo thời gian thực.
    """
    returns = data.pct_change().dropna()
    dates = returns.index.strftime('%Y-%m-%d').tolist()
    returns_np = returns.values
    T, N = returns_np.shape
    
    # 1. Khởi tạo
    weights = np.ones(N) / N # Bắt đầu bằng chia đều
    portfolio_wealth = [1.0] # Giá trị tài sản bắt đầu là 1.0 (100%)
    benchmark_wealth = [1.0] # Benchmark: Mua và nắm giữ đều (Equal Weight)
    
    # 2. Vòng lặp mô phỏng từng ngày
    for t in range(T):
        # --- CHIẾN LƯỢC OPS ---
        # Lợi nhuận ngày hôm nay của Portfolio
        day_ret = np.dot(weights, returns_np[t])
        
        # Cập nhật tổng tài sản
        new_wealth = portfolio_wealth[-1] * (1 + day_ret)
        portfolio_wealth.append(new_wealth)
        
        # Cập nhật trọng số cho ngày mai (Học từ hôm nay)
        # (Sử dụng lại logic EG có Constraints)
        if day_ret == 0: day_ret = 1e-10
        exponent = eta * returns_np[t] / day_ret
        exponent = np.clip(exponent, -30, 30) # Safer clip
        weights = weights * np.exp(exponent)
        weights /= np.sum(weights) # Chuẩn hóa
        weights = apply_max_weight_constraint(weights, max_weight) # Áp dụng giới hạn
        
        # --- BENCHMARK (BUY & HOLD) ---
        # Giả sử mua đều từ đầu và giữ nguyên, không tái cân bằng
        # Lợi nhuận trung bình của các mã
        bench_ret = np.mean(returns_np[t])
        new_bench = benchmark_wealth[-1] * (1 + bench_ret)
        benchmark_wealth.append(new_bench)
        
    return {
        "dates": dates, # Trục thời gian (bỏ ngày đầu tiên vì chưa có return)
        "strategy": portfolio_wealth[1:], # Bỏ giá trị khởi tạo 1.0
        "benchmark": benchmark_wealth[1:]
    }

def calculate_metrics(wealth_series):
    """Tính các chỉ số tài chính quan trọng"""
    wealth = np.array(wealth_series)
    # Handle division by zero or empty array
    if len(wealth) < 2: return {"total_return": 0, "sharpe_ratio": 0, "max_drawdown": 0}
        
    returns = np.diff(wealth) / wealth[:-1]
    
    if len(returns) == 0: return {"total_return": 0, "sharpe_ratio": 0, "max_drawdown": 0}

    # 1. Tổng Lợi nhuận
    total_return = (wealth[-1] - wealth[0]) / wealth[0]
    
    # 2. Sharpe Ratio (Giả định Risk-free = 0)
    # Annualized Sharpe = Mean / Std * sqrt(252)
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    sharpe = 0
    if std_ret > 1e-9:
        sharpe = (mean_ret / std_ret) * np.sqrt(252)
        
    # 3. Max Drawdown (Sụt giảm tối đa từ đỉnh)
    peak = np.maximum.accumulate(wealth)
    # Avoid division by zero if peak is 0 (unlikely for wealth starting at 1)
    drawdown = (wealth - peak) / peak
    max_drawdown = np.min(drawdown)
    
    return {
        "total_return": round(total_return * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_drawdown * 100, 2)
    }

# --- API MODELS ---
class NTFRequest(BaseModel):
    tickers: str # Dạng chuỗi: "BTC-USD, ETH-USD"
    lookback: int = 20

class OPSRequest(BaseModel):
    tickers: str
    eta: float = 0.05 # Learning rate

class BacktestRequest(BaseModel):
    tickers: str
    eta: float = 0.05
    max_weight: float = 1.0
    period: str = "1y" # 1 năm

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
        
        # Calculate missing tickers
        processed = data.columns.tolist()
        missing = list(set(ticker_list) - set(processed))
        
        return {"status": "success", "data": results, "missing": missing}
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

@app.post("/api/backtest")
def backtest_endpoint(req: BacktestRequest):
    ticker_list = [t.strip() for t in req.tickers.split(",")]
    if len(ticker_list) < 2:
         raise HTTPException(status_code=400, detail="Cần ít nhất 2 mã để Backtest.")
    try:
        # Lấy dữ liệu lịch sử dài hạn
        data = get_data(ticker_list, period=req.period)
        
        # Chạy giả lập
        sim_result = run_backtest_simulation(data, req.eta, req.max_weight)
        
        # Tính chỉ số
        stats_strat = calculate_metrics(sim_result["strategy"])
        stats_bench = calculate_metrics(sim_result["benchmark"])
        
        return {
            "status": "success",
            "chart_data": sim_result,
            "metrics": {
                "strategy": stats_strat,
                "benchmark": stats_bench
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

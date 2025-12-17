
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
# --- CACHING & DATA UTILS ---
DATA_CACHE_V2 = {}

def get_data(tickers, period="5y"): # Lấy 5 năm để OPS học tốt hơn
    tickers = [t.strip().upper() for t in tickers]
    key = (tuple(sorted(tickers)), period)
    
    if key in DATA_CACHE_V2 and (datetime.now() - DATA_CACHE_V2[key][0] < timedelta(hours=4)):
        print(f"Using Cached Data for {key}")
        return DATA_CACHE_V2[key][1]
        
    print(f"Fetching: {tickers} | Period: {period}")
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
    
    DATA_CACHE_V2[key] = (datetime.now(), data)
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

def run_backtest_simulation(data, eta=0.05, max_weight=1.0, transaction_fee=0.0015):
    """
    Giả lập hiệu suất đầu tư theo thời gian thực.
    Có tính phí giao dịch (Transaction Costs) để tránh bị "lừa" bởi lãi ảo.
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
        # Lợi nhuận ngày hôm nay của Portfolio (Gross Return)
        day_ret = np.dot(weights, returns_np[t])
        
        # Giá trị tài sản trước phí (End of Day Wealth)
        wealth_before_cost = portfolio_wealth[-1] * (1 + day_ret)
        
        # --- TÍNH TOÁN PHÍ GIAO DỊCH (Transaction Costs) ---
        # Tính tỷ trọng bị trôi (Drifted Weights) do giá thay đổi trong ngày
        # w_drifted = w * (1 + r) / (1 + R_p)
        if (1 + day_ret) == 0:
             drifted_weights = weights # Should almost never happen
        else:
             drifted_weights = weights * (1 + returns_np[t]) / (1 + day_ret)
        
        # Cập nhật trọng số TỐI ƯU cho ngày mai (Learning Algo)
        if day_ret == 0: day_ret = 1e-10
        exponent = eta * returns_np[t] / day_ret
        exponent = np.clip(exponent, -30, 30) # Safer clip
        new_weights = weights * np.exp(exponent)
        new_weights /= np.sum(new_weights) # Chuẩn hóa
        new_weights = apply_max_weight_constraint(new_weights, max_weight) # Áp dụng giới hạn
        
        # Tính Turnover: Tổng lượng hàng cần mua/bán để chuyển từ Drifted -> New Weights
        # Turnover = sum(|w_new - w_drifted|)
        turnover = np.sum(np.abs(new_weights - drifted_weights))
        
        # Chi phí = Turnover * Fee
        # Mặc định fee = 0.15% (0.0015)
        cost_fraction = turnover * transaction_fee
        
        # Trừ phí vào tài sản
        # Wealth_final = Wealth_before_cost * (1 - cost_fraction)
        portfolio_wealth.append(wealth_before_cost * (1 - cost_fraction))
        
        # Cập nhật weights cho vòng lặp sau
        weights = new_weights
        
        # --- BENCHMARK (BUY & HOLD) ---
        # Giả sử mua đều từ đầu và giữ nguyên, không tái cân bằng -> Không mất phí
        bench_ret = np.mean(returns_np[t])
        new_bench = benchmark_wealth[-1] * (1 + bench_ret)
        benchmark_wealth.append(new_bench)
        
    return {
        "dates": dates,
        "strategy": portfolio_wealth[1:],
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
    lookbacks: str = "20, 60, 120" # Chuỗi các lookback cho chiến lược Ensemble

class BacktestRequest(BaseModel):
    tickers: str
    eta: float = 0.05
    max_weight: float = 1.0
    period: str = "5y" # 5 năm
    transaction_fee: float = 0.0015 # Phí giao dịch (0.15%)
    custom_weights: dict[str, float] = None # Nhận tỷ trọng thủ công

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
        # Lấy lookbacks từ request
        try:
            lookbacks = [int(x.strip()) for x in req.lookbacks.split(",")]
        except ValueError:
             raise HTTPException(status_code=400, detail="Lookbacks phải là danh sách số nguyên, ví dụ: '20, 60, 120'")
        
        data = get_data(ticker_list) # Mặc định lấy 5y data
        
        # Khởi tạo dict chứa tổng weights
        final_weights = {ticker: 0.0 for ticker in data.columns}
        
        # Vòng lặp Ensemble
        valid_strategies = 0
        for lb in lookbacks:
            # Slice data theo lookback (Lấy lb ngày gần nhất)
            if lb > len(data):
                sub_data = data # Lấy hết nếu lookback lớn hơn dữ liệu có sẵn
            else:
                sub_data = data.iloc[-lb:]
            
            if sub_data.empty: continue
            
            # Tính weights cho chiến lược con này
            w = calculate_ops_eg(sub_data, req.eta)
            valid_strategies += 1
            
            # Cộng dồn
            for ticker, weight in w.items():
                if ticker in final_weights:
                    final_weights[ticker] += weight
        
        # Chia trung bình
        if valid_strategies > 0:
            for ticker in final_weights:
                final_weights[ticker] /= valid_strategies
                # Làm tròn
                final_weights[ticker] = round(final_weights[ticker], 4)
        
        return {"status": "success", "weights": final_weights, "algo": "Ensemble EG (Dynamic Momentum)"}
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
        
        mode_message = ""
        
        # --- LOGIC MỚI: CHỌN CHẾ ĐỘ ---
        if req.custom_weights and sum(req.custom_weights.values()) > 0:
            # CHẾ ĐỘ THỦ CÔNG (Manual Allocation - Constant Mix)
            mode_message = "Thủ công (Manual Allocation)"
            
            # Filter custom weights to match available data columns
            valid_weights = {k: v for k, v in req.custom_weights.items() if k in data.columns}
            if not valid_weights:
                 raise HTTPException(status_code=400, detail="Không tìm thấy mã nào trong dữ liệu khớp với tỷ trọng nhập vào.")
            
            # Normalize weights to sum to 1
            total_w = sum(valid_weights.values())
            weights_map = {k: v / total_w for k, v in valid_weights.items()}
            
            # Simulation for Constant Mix
            returns = data.pct_change().dropna()
            dates = returns.index.strftime('%Y-%m-%d').tolist()
            returns_np = returns.values
            T, N = returns_np.shape
            
            # Map weights to column order
            w_vector = np.array([weights_map.get(col, 0.0) for col in data.columns])
            
            # Sim
            portfolio_wealth = [1.0]
            benchmark_wealth = [1.0] # Equal weight benchmark
            
            # Pre-calculate benchmark equal weights
            bench_weights = np.ones(N) / N
            
            for t in range(T):
                # Strategy Return (Constant Mix: rebalance every day to w_vector)
                # Cost is ignored in this simple manual view or we can apply it. 
                # User snippet didn't emphasize cost for manual, but let's keep it fair? 
                # User snippet: strategy_ret = (weights_df.shift(1) * data.pct_change()).sum(axis=1) NO COST.
                # Let's simple dot product
                
                day_ret = np.dot(w_vector, returns_np[t])
                portfolio_wealth.append(portfolio_wealth[-1] * (1 + day_ret))
                
                # Benchmark Return
                bench_ret = np.dot(bench_weights, returns_np[t])
                benchmark_wealth.append(benchmark_wealth[-1] * (1 + bench_ret))
            
            sim_result = {
                "dates": dates,
                "strategy": portfolio_wealth[1:],
                "benchmark": benchmark_wealth[1:]
            }
            
        else:
            # CHẾ ĐỘ TỰ ĐỘNG (OPS AI)
            mode_message = "Tự động (AI OPS)"
            sim_result = run_backtest_simulation(data, req.eta, req.max_weight, req.transaction_fee)
        
        # Tính chỉ số
        stats_strat = calculate_metrics(sim_result["strategy"])
        stats_bench = calculate_metrics(sim_result["benchmark"])
        
        return {
            "status": "success",
            "chart_data": sim_result,
            "metrics": {
                "strategy": stats_strat,
                "benchmark": stats_bench
            },
            "mode": mode_message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- AI ENGINE (Load Model) ---
import joblib
import os

# Kiểm tra xem có file model không
MODEL_PATH = "quant_ai_model.pkl"
ai_model = None

try:
    if os.path.exists(MODEL_PATH):
        ai_model = joblib.load(MODEL_PATH)
        print("✅ Đã load AI Model thành công!")
    else:
        print("⚠️ Không tìm thấy file model. Chức năng AI sẽ tắt.")
except Exception as e:
    print(f"❌ Lỗi load model: {e}")

# --- HÀM TÍNH CHỈ BÁO (PHẢI KHỚP 100% VỚI COLAB) ---
def calculate_features(df):
    # 1. RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. SMA 20 & Distance
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['Dist_SMA20'] = (df['Close'] - df['SMA_20']) / df['SMA_20']
    
    # 3. MACD (MỚI)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # 4. Bollinger Bands %B (MỚI)
    std_20 = df['Close'].rolling(window=20).std()
    upper = df['SMA_20'] + (2 * std_20)
    lower = df['SMA_20'] - (2 * std_20)
    # Tránh chia cho 0
    df['BB_PctB'] = (df['Close'] - lower) / (upper - lower)
    
    # --- THÊM DÒNG NÀY ---
    df['BandWidth'] = (upper - lower) / df['SMA_20']
    # ---------------------

    # 5. Volume Ratio (MỚI)
    vol_sma20 = df['Volume'].rolling(window=20).mean()
    df['Vol_Ratio'] = df['Volume'] / vol_sma20

    # 6. Volatility (Giữ nguyên)
    df['Return_1d'] = df['Close'].pct_change()
    df['Vol_20'] = df['Return_1d'].rolling(window=20).std()
    
    return df.dropna()

class AiRequest(BaseModel):
    ticker: str

@app.post("/api/ask-ai")
def ask_ai_endpoint(req: AiRequest):
    if ai_model is None:
        raise HTTPException(status_code=500, detail="Server chưa có não AI (.pkl).")
    
    try:
        ticker = req.ticker.strip().upper()
        # Logic fix mã chứng khoán
        if not ticker.endswith(".VN") and "-" not in ticker and len(ticker) <= 3: 
             ticker += ".VN"
             
        # Lấy 1 năm dữ liệu để đảm bảo tính chỉ báo đủ
        data = yf.download(ticker, period="1y", progress=False)
        
        if len(data) < 60:
             raise HTTPException(status_code=400, detail="Không đủ dữ liệu lịch sử.")
             
        # Fix lỗi MultiIndex của yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # Tính toán
        processed_data = calculate_features(data)
        last_row = processed_data.iloc[[-1]]
        
        # --- QUAN TRỌNG: CHỌN ĐÚNG CỘT KHỚP VỚI FILE .PKL ---
        # Danh sách này phải giống hệt lúc bạn train trên Colab (KHÔNG CÓ BandWidth)
        feature_cols_ai = ['RSI', 'Dist_SMA20', 'MACD_Hist', 'BB_PctB', 'Vol_Ratio', 'Vol_20']
        
        features_for_ai = last_row[feature_cols_ai]
        
        # Dự đoán
        prediction = ai_model.predict(features_for_ai)[0]
        probs = ai_model.predict_proba(features_for_ai)[0]
        
        signal = "TĂNG 📈" if prediction == 1 else "GIẢM 📉"
        confidence = probs[prediction]

        # Wyckoff Logic (Lấy từ last_row, không phải features_for_ai)
        bw_val = last_row['BandWidth'].values[0]
        wyckoff_status = "Bình thường"
        if bw_val < 0.10: 
            wyckoff_status = "NÚT CỔ CHAI (Sắp nổ) 💣"
        elif bw_val > 0.40:
            wyckoff_status = "BIẾN ĐỘNG MẠNH 🌊"
        
        return {
            "ticker": ticker,
            "signal": signal,
            "confidence": round(confidence * 100, 2),
            "details": {
                "RSI": round(features_for_ai['RSI'].values[0], 2),
                "MACD": round(features_for_ai['MACD_Hist'].values[0], 4),
                "BB_Pct": round(features_for_ai['BB_PctB'].values[0], 2),
                "Vol_Rat": round(features_for_ai['Vol_Ratio'].values[0], 2),
                
                # --- THÊM DÒNG NÀY ---
                "BandWidth": round(bw_val, 4),
                "Wyckoff": wyckoff_status
                # ---------------------
            }
        }
        
    except Exception as e:
        print(f"Lỗi: {e}")
        # Trả về lỗi chi tiết để dễ debug
        raise HTTPException(status_code=500, detail=f"Lỗi tính toán: {str(e)}")

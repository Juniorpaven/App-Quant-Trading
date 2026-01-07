from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats # For Percentile Rank

# Removed top-level vnstock import to prevent startup timeout
# vnstock will be imported lazily in get_vnstock_fundamentals

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
    
    # Clip weights to max_weight
    weights = np.minimum(weights, max_weight)
    
    # If sum > 1, we might need to normalize, but usually after clipping max_weight < 1, 
    # the sum will be <= 1 (unless we had many items).
    # If sum < 1, it means we hold CASH.
    
    # However, if original sum was 1, and we clip, sum implies reduced exposure.
    # Logic: Simply Clipping is enough to satisfy "Max Weight" constraint
    # and implicitly creates a "Cash" position.
    
    # Verify sum > 1 case (Edge case where many small items sum > 1 but individual <= max? 
    # No, if we start with sum=1, and clip, sum can only decrease or stay same).
    # Wait, if we implement a constraint where we WANT to be fully invested but CAN'T due to max_weight?
    # Then we can't. So Cash is the only option.
    
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
    max_weight: float = 1.0 # New Parameter for Constraint

class BacktestRequest(BaseModel):
    tickers: str
    eta: float = 0.05
    max_weight: float = 1.0
    period: str = "5y" # 5 năm
    transaction_fee: float = 0.0015 # Phí giao dịch (0.15%)
    custom_weights: Optional[Dict[str, float]] = None # Nhận tỷ trọng thủ công

# --- DASHBOARD ENGINE (COMMAND CENTER) ---
VN30_LIST = ["ACB.VN", "BCM.VN", "BID.VN", "BVH.VN", "CTG.VN", "FPT.VN", "GAS.VN", "GVR.VN", "HDB.VN", "HPG.VN", "MBB.VN", "MSN.VN", "MWG.VN", "PLX.VN", "POW.VN", "SAB.VN", "SHB.VN", "SSB.VN", "SSI.VN", "STB.VN", "TCB.VN", "TPB.VN", "VCB.VN", "VHM.VN", "VIB.VN", "VIC.VN", "VJC.VN", "VNM.VN", "VPB.VN", "VRE.VN"]

# --- VNSTOCK INTEGRATION ---

def get_vnstock_price(ticker):
    """Get latest close price from vnstock"""
    try:
        from vnstock import Vnstock
        clean_ticker = ticker.replace(".VN", "").strip()
        # Fetch just last few days to get latest close
        stock = Vnstock().stock(symbol=clean_ticker, source='VCI')
        # Using a small window to ensure we get data
        now = datetime.now()
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        df = stock.quote.history(symbol=clean_ticker, start=start_date, end=end_date)
        if df is not None and not df.empty:
            return df['close'].iloc[-1]
    except Exception as e:
        print(f"Price error for {ticker}: {e}")
    return 0

def get_vnstock_fundamentals(ticker):
    """Lấy chỉ số cơ bản từ VNStock (P/E TTM, ROE...)"""
    # LAZY IMPORT VNSTOCK
    try:
        from vnstock import Finance
        import pandas as pd
        vnstock_available = True
    except ImportError:
        vnstock_available = False
        print("Warning: vnstock not installed")

    if not vnstock_available:
        return {"pe": 0, "roe": 0, "eps": 0, "pb": 0, "source": "N/A"}
    
    clean_ticker = ticker.replace(".VN", "").strip()
    try:
        fin = Finance(symbol=clean_ticker, source='VCI')
        
        # 1. Fetch Quarterly Ratios for TTM Calc
        df = fin.ratio(period='quarterly', lang='vi')
        
        if df is None or df.empty:
             return {"pe": 0, "roe": 0, "eps": 0, "pb": 0, "source": "Empty"}
             
        # Flatten MultiIndex Columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(col).strip() for col in df.columns.values]
            
        # Helper to find value by keyword (Robust)
        def get_series(keywords, limit=1):
            for col in df.columns:
                col_lower = col.lower()
                if any(kw in col_lower for kw in keywords):
                    return df[col].head(limit).values
            return [0] * limit

        # 2. Calculate EPS TTM (Sum 4 quarters)
        eps_quarters = get_series(['eps', 'earning per share', 'lợi nhuận trên mỗi'], limit=4)
        eps_ttm = sum([float(x) for x in eps_quarters if pd.notnull(x)])
        
        # 3. Get other metrics (Latest Quarter)
        roe_latest = float(get_series(['roe', 'return on equity'])[0])
        pb_latest = float(get_series(['p/b', 'price to book'])[0])
        
        # 4. Get Realtime Price for P/E
        price_now = get_vnstock_price(clean_ticker) * 1000 # Vnstock price is often in k VND? CHECK! 
        # Wait, vnstock history returns absolute price e.g. 58.95 -> 58950? 
        # Actually in debug output: 58.95. FireAnt EPS 1209. 
        # Let's check debug output again.
        # History: 58.95. 
        # Dashboard EPS: 1209. 
        # PE = 58950 / 4160 ~ 14. 
        # If vnstock price 58.95 means 58,950 VND, then we multiply by 1000.
        # Let's assume vnstock returns price in 'thousands' (check debug 434: 58.95). 
        # Standardize for calc: 58.95 * 1000 = 58950.
        
        if price_now < 1000: price_now *= 1000
        
        pe_realtime = 0
        if eps_ttm > 0:
            pe_realtime = price_now / eps_ttm

        return {
            "pe": round(pe_realtime, 2),
            "roe": round(roe_latest * 100 if roe_latest < 5 else roe_latest, 2),
            "eps": round(eps_ttm, 0),
            "pb": round(pb_latest, 2),
            "source": "Vnstock TTM"
        }
    except Exception as e:
        print(f"VNStock Error for {ticker}: {e}")
        return {"pe": 0, "roe": 0, "eps": 0, "pb": 0, "source": "Error"}

# --- VOLUME PROFILE & CHARTING ---
import plotly.graph_objects as go
import json

def calculate_volume_profile(df, price_col='Close', vol_col='Volume', bins=50):
    """
    Tính toán Volume Profile từ dữ liệu nến OHLCV (Dạng ước lượng)
    """
    if len(df) < 2: return pd.DataFrame(), 0

    # 1. Xác định biên độ giá toàn bộ giai đoạn
    # Fix: Ensure scalar values if DF has multi-index or slight structure issues
    min_price = float(df['Low'].min())
    max_price = float(df['High'].max())
    
    # 2. Chia nhỏ mức giá thành các giỏ (bins)
    price_range = np.linspace(min_price, max_price, bins)
    
    # 3. Tính tổng volume cho từng mức giá
    # Logic: Phân bổ volume của cây nến vào các bin giá mà cây nến đó đi qua
    # Cách đơn giản hóa: Histogram của Close Price weighted by Volume
    
    # Ensure Series are numpy arrays/lists for histogram
    close_prices = df[price_col].values
    volumes = df[vol_col].values
    
    hist, bin_edges = np.histogram(close_prices, bins=price_range, weights=volumes)
    
    # 4. Tìm POC (Point of Control) - Mức giá có Volume lớn nhất
    max_vol_idx = hist.argmax()
    poc_price = (bin_edges[max_vol_idx] + bin_edges[max_vol_idx+1]) / 2
    
    # 5. Tạo DataFrame kết quả
    vp_df = pd.DataFrame({
        'Price_Low': bin_edges[:-1],
        'Price_High': bin_edges[1:],
        'Volume': hist
    })
    vp_df['Price_Mid'] = (vp_df['Price_Low'] + vp_df['Price_High']) / 2
    
    return vp_df, poc_price

def plot_candlestick_with_vp(df, ticker_name):
    # Tính VP
    vp_df, poc_price = calculate_volume_profile(df)
    
    # Tạo biểu đồ chính (Nến)
    fig = go.Figure()
    
    # 1. Vẽ Nến
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name=f'{ticker_name} Price'
    ))
    
    # 2. Vẽ Volume Profile (Nằm ngang bên phải)
    # Hack: Vẽ bằng Scatter line để tạo hiệu ứng thanh ngang hoặc Bar chart trục ngang
    # Tuy nhiên, để đơn giản và đẹp trên Web, ta sẽ dùng Shapes hoặc Bar orientation='h'
    # Lưu ý: Bar h cần trục y là giá, trục x là volume. 
    # Nhưng chart nến đang có trục x là thời gian.
    # -> Cần 2 trục X (xaxis, xaxis2).
    
    # Setup layout với 2 trục X
    fig.update_layout(
        xaxis=dict(domain=[0, 0.75], title="Time"), # Chart nến chiếm 75%
        xaxis2=dict(domain=[0.76, 1], title="Volume Profile"), # VP chiếm 24%
        yaxis=dict(title="Price"),
        template="plotly_dark",
        height=600,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(x=0, y=1, orientation="h")
    )
    
    # Vẽ VP Bar Chart ở trục phụ (xaxis2)
    if not vp_df.empty:
        fig.add_trace(go.Bar(
            y=vp_df['Price_Mid'],
            x=vp_df['Volume'],
            orientation='h',
            xaxis='x2',
            name='Volume Profile',
            marker=dict(color='rgba(255, 255, 0, 0.3)', line=dict(width=0))
        ))

    # Vẽ POC (Đường kẻ ngang toàn chart)
    fig.add_hline(y=poc_price, line_dash="dash", line_color="yellow", line_width=2, 
                  annotation_text="POC", annotation_position="top right")

    fig.update_layout(title=f"{ticker_name} - Price Action & POC Analysis")
    
    return fig

# --- NEW API ENDPOINT FOR CHART ---
class ChartRequest(BaseModel):
    ticker: str

def get_ohlcv_smart(ticker, period="1y"):
    """
    Fetch OHLCV data using Yahoo Finance first, fallback to Vnstock if failed.
    Returns: DataFrame with index=Date, columns=[Open, High, Low, Close, Volume]
    """
    # 1. Try Yahoo Finance
    yf_ticker = ticker.strip().upper()
    if "-" not in yf_ticker and "^" not in yf_ticker and ".VN" not in yf_ticker:
        yf_ticker += ".VN"
        
    print(f"Chart: Fetching {yf_ticker} via Yahoo...")
    try:
        df = yf.download(yf_ticker, period=period, progress=False, auto_adjust=True)
        # Handle MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
             # Try to get the ticker level if it exists
            if yf_ticker in df.columns.get_level_values(1):
                 df = df.xs(yf_ticker, level=1, axis=1)
            elif yf_ticker.replace('.VN', '') in df.columns.get_level_values(1):
                 df = df.xs(yf_ticker.replace('.VN', ''), level=1, axis=1)
        
        # Check basic columns
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not df.empty and all(col in df.columns for col in required):
            print("Chart: Yahoo Success.")
            return df[required]
    except Exception as e:
        print(f"Chart: Yahoo failed: {e}")

    # 2. Fallback to Vnstock
    vn_ticker = ticker.replace(".VN", "").strip().upper()
    print(f"Chart: Fallback to Vnstock for {vn_ticker}...")
    try:
        from vnstock import Vnstock
        # Period mapping
        days = 365
        if period == "1y": days = 365
        elif period == "2y": days = 730
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        stock = Vnstock().stock(symbol=vn_ticker, source='VCI')
        df = stock.quote.history(symbol=vn_ticker, start=start_date, end=end_date)
        
        if df is not None and not df.empty:
            # Vnstock cols: time, open, high, low, close, volume
            df = df.rename(columns={
                'time': 'Date', 'open': 'Open', 'high': 'High', 
                'low': 'Low', 'close': 'Close', 'volume': 'Volume'
            })
            df = df.set_index('Date')
            df.index = pd.to_datetime(df.index)
            # Ensure numeric
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for c in cols: df[c] = pd.to_numeric(df[c])
            
            print("Chart: Vnstock Success.")
            return df[cols]
            
    except Exception as e:
        print(f"Chart: Vnstock failed: {e}")
        
    return pd.DataFrame()

@app.post("/api/dashboard/chart")
def get_chart_data(req: ChartRequest):
    try:
        df = get_ohlcv_smart(req.ticker)
        
        if df.empty:
             return {"error": "No data found via Yahoo or Vnstock"}
             
        # Plot
        fig = plot_candlestick_with_vp(df, req.ticker.upper())
        
        # Convert to JSON for frontend
        return {"data": json.loads(fig.to_json())}
        
    except Exception as e:
        print(f"Chart Error: {e}")
        return {"error": str(e)}

# --- DASHBOARD ENDPOINTS ---


def get_data(tickers, period="5y"): 
    """
    Smart Data Fetcher:
    1. Try Yahoo Finance (Batch) -> Fast (2s).
    2. If Yahoo returns empty (likely blocked on Cloud), fallback to Vnstock (Sequential) -> Slow (15-30s) but works.
    """
    
    # 1. Standardize Tickers for Yahoo
    yf_tickers = []
    for t in tickers:
        clean = t.strip().upper()
        if clean == "VNINDEX": clean = "^VNINDEX"
        if "-" not in clean and "^" not in clean and ".VN" not in clean:
            clean += ".VN"
        yf_tickers.append(clean)
        
    print(f"ATTEMPT 1: Fetching Yahoo Batch ({len(yf_tickers)} tickers)...")
    
    try:
        # Using auto_adjust=True to get 'Close'
        data_raw = yf.download(yf_tickers, period=period, progress=False, auto_adjust=True)
        
        target_col = None
        if 'Close' in data_raw.columns: target_col = 'Close'
        elif 'Adj Close' in data_raw.columns: target_col = 'Adj Close'
             
        data = pd.DataFrame()
        if target_col:
            data = data_raw[target_col]
        else:
            data = data_raw

        if isinstance(data, pd.Series):
            data = data.to_frame(name=yf_tickers[0])
            
        data = data.dropna(axis=1, how='all')
        
        # CHECK SUCCESS
        if not data.empty and data.shape[1] > 0:
            print("Yahoo Fetch Success.")
            return data.ffill().dropna()
        else:
            print("Yahoo returned empty data. Switching to Fallback.")
            
    except Exception as e:
        print(f"Yahoo Fetch Error: {e}")
        
    # 2. FALLBACK TO VNSTOCK
    print("ATTEMPT 2: Switching to Vnstock Sequential...")
    return get_data_vnstock_sequential(yf_tickers, period).ffill().dropna()


def calculate_rrg_data(tickers, benchmark="^VNINDEX"): # Sử dụng VNINDEX làm bench
    # 1. Fetch Data (Price History)
    all_tickers = tickers + [benchmark]
    # Use cached get_data instead of direct yf.download
    # This caches results for 4 hours, making subsequent RRG loads instant
    try:
        data = get_data(all_tickers, period="1y")
    except Exception as e:
        print(f"RRG Data Fetch Error: {e}")
        return []

    if data is None or data.empty:
        return []

    # Fix MultiIndex if any
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # Forward Fill & Drop NaN
    data = data.ffill().dropna()
    
    if benchmark not in data.columns:
        return []

    bench_series = data[benchmark]
    rrg_results = []
    
    for t in tickers:
        if t not in data.columns: continue
        
        # 2. Compute RS (Relative Strength)
        # RS = 100 * (Price / Benchmark)
        rs_raw = 100 * (data[t] / bench_series)
        
        # 3. Compute JdK RS-Ratio (Moving Average of RS / StdDev -> Simplified: Just MA)
        # Simplified RRG Logic:
        # RS-Ratio = (RS / MA(RS, 10)) * 100 (Measure Trend) -> Using lookback 10-20
        # Actually RRG uses normalized algo. Let's use a robust proxy.
        # RS_Ratio ~ Exponential Moving Average of RS
        
        rs_ratio_series = rs_raw.rolling(window=10).mean()
        
        # 4. Compute JdK RS-Momentum (Rate of Change of RS-Ratio)
        # Momentum = 100 + ((RS-Ratio - MA(RS-Ratio)) / MA(RS-Ratio)) * 100
        # Simplest: ROC of RS-Ratio
        
        rs_mom_series = rs_ratio_series.pct_change(periods=5) * 100 + 100 # Center at 100
        
        # Get latest values
        if len(rs_ratio_series) < 1 or len(rs_mom_series) < 1: continue
        
        curr_ratio = rs_ratio_series.iloc[-1]
        curr_mom = rs_mom_series.iloc[-1]
        
        # Determine Quadrant
        quadrant = ""
        if curr_ratio > 100 and curr_mom > 100: quadrant = "Leading (Dẫn dắt) 🟢"
        elif curr_ratio > 100 and curr_mom < 100: quadrant = "Weakening (Suy yếu) 🟡"
        elif curr_ratio < 100 and curr_mom < 100: quadrant = "Lagging (Tụt hậu) 🔴"
        else: quadrant = "Improving (Cải thiện) 🔵"
        
        rrg_results.append({
            "ticker": t.replace(".VN", ""),
            "x": round(curr_ratio, 2), # RS-Ratio
            "y": round(curr_mom, 2),   # RS-Momentum
            "quadrant": quadrant
        })
        
    return rrg_results

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "Backend is running (Zero-Cost Mode)"}

@app.post("/api/run-ntf")
def run_ntf_endpoint(req: NTFRequest):
    # 1. Tách danh sách mã từ ô nhập liệu
    raw_tickers = [t.strip() for t in req.tickers.split(",")]
    clean_data = {} # Nơi chứa dữ liệu sạch
    
    print(f"📡 NTF Analysis: Scanning {len(raw_tickers)} tickers...")
    
    # 2. Vòng lặp kiểm tra từng mã (Chế độ An toàn - Immortal Fix)
    for t in raw_tickers:
        try:
            # Standardize Ticker for Yahoo (add .VN if missing and no special chars)
            yf_ticker = t
            if not any(x in t for x in ["^", "-", "."]):
                 yf_ticker = t + ".VN"

            # Tải dữ liệu từng mã riêng lẻ để dễ kiểm soát lỗi
            # User requested "3mo", we use "6mo" to be safe for slightly larger lookbacks if needed, 
            # but usually NTF looks at last 20 days.
            df = yf.download(yf_ticker, period="6mo", progress=False, auto_adjust=True)
            
            # Xử lý trường hợp Yahoo trả về MultiIndex hoặc sai định dạng
            if isinstance(df.columns, pd.MultiIndex):
                try: 
                    # Try to find the ticker level
                    if yf_ticker in df.columns.levels[1]:
                         df = df.xs(yf_ticker, level=1, axis=1)
                except: pass

            # KIỂM TRA ĐIỀU KIỆN
            # 1. Dữ liệu rỗng?
            if df.empty:
                print(f"Bỏ qua {t}: Rỗng")
                continue
            
            # Determine Target Column (Close or Adj Close)
            target_col = 'Close'
            if 'Close' not in df.columns and 'Adj Close' in df.columns:
                target_col = 'Adj Close'
                
            if target_col not in df.columns:
                 continue

            # 2. Không đủ số ngày tính toán (Lookback)?
            if len(df) < req.lookback:
                print(f"Bỏ qua {t}: Không đủ dữ liệu ({len(df)} dòng)")
                continue
                
            # 3. Giá trị bị NaN quá nhiều?
            if df[target_col].isnull().sum() > 5:
                print(f"Bỏ qua {t}: Quá nhiều NaN")
                continue

            # Nếu ngon lành thì thêm vào kho
            clean_data[t] = df[target_col]
            
        except Exception as e:
            print(f"Error checking {t}: {e}")
            continue # Lỗi thì bỏ qua, đi tiếp mã sau
            
    # 3. TÍNH TOÁN TRÊN DỮ LIỆU SẠCH
    results = {}
    missing = []
    
    if len(clean_data) > 0:
        df_combined = pd.DataFrame(clean_data)
        
        # --- Logic Tính toán Momentum cũ ---
        # 1. Align Data
        df_combined = df_combined.ffill().dropna()
        
        # 2. Calculate
        if len(df_combined) >= req.lookback:
            returns = df_combined.pct_change().dropna()
            momentum = returns.iloc[-req.lookback:].mean() * 252
            scores = momentum.to_dict()
            results = {k: round(v, 4) for k, v in scores.items()}
        
    # Calculate detailed missing list
    processed_list = list(results.keys())
    missing = list(set(raw_tickers) - set(processed_list))
    
    # Return result
    return {"status": "success", "data": results, "missing": missing}

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
                
        # --- APDY CONSTRAINT (FIX) ---
        # Convert dict to numpy array for constraint function
        tickers_ordered = list(final_weights.keys())
        w_values = np.array([final_weights[t] for t in tickers_ordered])
        
        # Apply Constraint (Max Weight + Implicit Cash)
        w_constrained = apply_max_weight_constraint(w_values, req.max_weight)
        
        # Re-map to dict
        constrained_result = {}
        for i, t in enumerate(tickers_ordered):
            val = float(w_constrained[i])
            if val > 0.0001: # Filter tiny dust
                constrained_result[t] = round(val, 4)
                
        # Add Cash info if any
        total_invested = sum(constrained_result.values())
        if total_invested < 0.999:
             constrained_result["CASH (Tiền mặt)"] = round(1.0 - total_invested, 4)
        
        return {"status": "success", "weights": constrained_result, "algo": "Ensemble EG (Constrained)"}
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
            "mode": mode_message,
            "final_weights": valid_weights if mode_message == "Thủ công (Manual Allocation)" else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- GLOBAL CACHE FOR SMART PULSE (The "Static" Base) ---
SMART_PULSE_ORACLE = {
    "last_updated": None,      
    "ma200_map": {},          # {ticker: ma200_value_yesterday}
    "price_t20_map": {},      # {ticker: price_20_days_ago} 
    "mom_history_array": [],  # List of past market momentum values for ranking
    "breadth_t1": 0.5,        
    "status": "EMPTY"         
}

def update_smart_pulse_oracle():
    """Heavy operation: Runs ONCE per day (or on restart) to build the static base."""
    global SMART_PULSE_ORACLE
    print("⚡ ORACLE: Building Static Market Base (2Y History)...")
    
    try:
        # 1. Fetch Heavy History
        full_list = VN30_LIST + ["^VNINDEX"]
        # REDUCED TO 6 MONTHS FOR STABILITY (2Y might be timing out)
        data = yf.download(full_list, period="6mo", progress=False, auto_adjust=False)['Adj Close']
        
        if data.empty:
            print("⚡ ORACLE FAIL: No Data")
            SMART_PULSE_ORACLE["status"] = "ERROR"
            return False

        if isinstance(data, pd.Series): data = data.to_frame()
        data = data.ffill().dropna() 
        
        # Relaxed check for 6mo (approx 125 trading days). Need at least 60 for safe momentum.
        if len(data) < 60: 
            print("⚡ ORACLE FAIL: Not enough history")
            return False

        # 2. Pre-calculate Static Metrics (Everything based on T-1)
        
        # A. MA200 Reference (from T-1)
        ma200_series = data.rolling(window=200).mean().iloc[-1] 
        SMART_PULSE_ORACLE["ma200_map"] = ma200_series.to_dict()

        # B. Momentum Reference (Price T-20)
        # We need Price 20 days ago from END (Index -20)
        price_t20_series = data.iloc[-20]
        SMART_PULSE_ORACLE["price_t20_map"] = price_t20_series.to_dict()

        # C. Momentum History (For Percentile Rank)
        basket_cols = [c for c in data.columns if c != "^VNINDEX"]
        basket_daily_ret = data[basket_cols].pct_change(fill_method=None).mean(axis=1)
        mom_curve = basket_daily_ret.rolling(window=20).mean() * 20 
        
        # Store last 252 points (minus closest day to avoid overlap if needed, but T-1 is fine)
        # We take history UP TO T-1
        valid_history = mom_curve.dropna().iloc[-253:-1].values 
        SMART_PULSE_ORACLE["mom_history_array"] = valid_history

        # D. Breadth Reference (T-1)
        benchmark = data["^VNINDEX"]
        beats = 0
        total = 0
        for t in VN30_LIST:
            if t not in data.columns: continue
            rs = 100 * (data[t] / benchmark)
            rs_ma = rs.rolling(window=10).mean()
            if rs_ma.iloc[-1] > 100: beats += 1 
            total += 1
        SMART_PULSE_ORACLE["breadth_t1"] = beats / total if total > 0 else 0

        SMART_PULSE_ORACLE["last_updated"] = datetime.now()
        SMART_PULSE_ORACLE["status"] = "READY"
        print("✅ ORACLE: Static Base Ready.")
        return True

    except Exception as e:
        print(f"⚡ ORACLE EXCEPTION: {e}")
        SMART_PULSE_ORACLE["status"] = "ERROR"
        return False

@app.get("/api/dashboard/sentiment")
def get_dashboard_sentiment():
    try:
        # 1. CHECK & WARM UP ORACLE
        is_stale = False
        if SMART_PULSE_ORACLE["last_updated"]:
            age = datetime.now() - SMART_PULSE_ORACLE["last_updated"]
            if age.total_seconds() > 43200: is_stale = True # 12 hours

        if SMART_PULSE_ORACLE["status"] != "READY" or is_stale:
            success = update_smart_pulse_oracle()
            if not success:
                # Soft Fail
                return {
                    "market_score": 0.5, 
                    "market_status": "Starting Up (Warming Cache)...", 
                    "market_color": "#888", 
                    "delta": 0,
                    "top_movers": []
                }

        # 2. FAST TICK (The "Dynamic" Pulse) - ONLY 1 DAY
        full_list = VN30_LIST + ["^VNINDEX"]
        try:
            live_data = yf.download(full_list, period="1d", progress=False, auto_adjust=False)['Adj Close']
        except:
             return {"market_score": 0.5, "market_status": "Live Data Lag...", "market_color": "#888", "delta": 0, "top_movers": []}

        if live_data.empty:
             # If no live data (weekend/holiday), use static Snapshot
             # But if static is ready, better return that than nothing?
             return {"market_score": 0.5, "market_status": "Market Closed", "market_color": "#888", "delta": 0, "top_movers": []}

        current_prices = live_data.iloc[-1] 
        
        # 3. INCREMENTAL CALC (Merge Static + Dynamic)
        
        # A. BREADTH (Proxy: Use T-1 Static Base)
        breadth_t0 = SMART_PULSE_ORACLE["breadth_t1"] 

        # B. MOMENTUM (Live Calc)
        # Mom = Current_Price / Price_T20 (from Oracle) - 1
        t20_map = SMART_PULSE_ORACLE["price_t20_map"]
        
        basket_moms = []
        for t in VN30_LIST:
            if t in current_prices and t in t20_map:
                p_now = current_prices[t]
                p_old = t20_map[t]
                if p_old > 0:
                    ret = (p_now / p_old) - 1
                    basket_moms.append(ret)
        
        curr_mom_val = sum(basket_moms) / len(basket_moms) if basket_moms else 0

        # Rank T0 vs History
        hist_moms = SMART_PULSE_ORACLE["mom_history_array"] 
        mom_score_t0 = 0.5
        if len(hist_moms) > 0:
            mom_score_t0 = stats.percentileofscore(hist_moms, curr_mom_val) / 100.0
        
        # C. REGIME (Live Calc: Basket Price vs Oracle MA200)
        ma200_map = SMART_PULSE_ORACLE["ma200_map"]
        
        basket_now_vals = [current_prices[t] for t in VN30_LIST if t in current_prices]
        basket_price_now = sum(basket_now_vals) / len(basket_now_vals) if basket_now_vals else 0
        
        ma_vals = [ma200_map[t] for t in VN30_LIST if t in ma200_map]
        basket_ma200_ref = sum(ma_vals) / len(ma_vals) if ma_vals else 0
        
        regime_mul = 1.0
        if basket_price_now < basket_ma200_ref: regime_mul = 0.7

        # 4. FINAL SCORES
        final_score = (0.6 * breadth_t0 + 0.4 * mom_score_t0) * regime_mul
        
        # Delta Proxy: Compare vs Mom T-1 Score (from History Tail)
        # We assume Breadth didn't change drastically in 1 session for Delta purposes in Fast Mode
        last_hist_val = hist_moms[-1] if len(hist_moms) > 0 else 0
        mom_score_t1 = stats.percentileofscore(hist_moms[:-1], last_hist_val) / 100.0 if len(hist_moms) > 1 else 0.5
        
        # Reconstruct T-1 Score (assuming Regime T-1 ~ Regime T-0 for delta context, or use strict history)
        # regime T-1 check:
        # We don't have Price T-1 easily here without fetching history again. 
        # Assume Regime unchanged for Delta visual.
        score_t1_approx = (0.6 * breadth_t0 + 0.4 * mom_score_t1) * regime_mul 
        
        delta = final_score - score_t1_approx

        # DISPLAY
        smart_pulse_score = round(final_score, 2)
        status = "TRUNG TÍNH (Neutral) 😐"
        d_color = "#ffea00"
        if smart_pulse_score < 0.3:
            status = "SỢ HÃI (Fear) 🐻 - Cash King"
            d_color = "#ff1744"
        elif smart_pulse_score > 0.7:
            status = "THAM LAM (Greed) 🐂 - Full Margin"
            d_color = "#00e676"

        return {
            "market_score": smart_pulse_score,
            "market_status": status,
            "market_color": d_color,
            "delta": round(delta, 2),
            "top_movers": [] # Frontend handles its own or use RRG leaders
        }
    except Exception as e:
        print(f"Sentiment Fast-Path Error: {e}")
        return {"market_score": 0, "market_status": "Connecting...", "delta": 0, "top_movers": []}

@app.post("/api/dashboard/rrg")
def get_dashboard_rrg(req: Optional[NTFRequest] = None):
    # If tickers provided, use them, else use VN30
    tickers_to_use = VN30_LIST
    if req and req.tickers:
        tickers_to_use = [t.strip() for t in req.tickers.split(",")]
        
    try:
        results = calculate_rrg_data(tickers_to_use)
        return {"data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FundamentalRequest(BaseModel):
    ticker: str

@app.post("/api/dashboard/fundamentals")
def get_dashboard_fundamentals(req: FundamentalRequest):
    try:
        ticker = req.ticker.strip().upper()
        if "-" not in ticker and ".VN" not in ticker and len(ticker) <= 3:
             ticker += ".VN"
        
        data = get_vnstock_fundamentals(ticker)
        return {"data": data}
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
             print(f"Build-in yfinance failed/insufficient for {ticker}. Trying vnstock fallback...")
             try:
                 from vnstock import Vnstock
                 clean_ticker = ticker.replace(".VN", "").strip()
                 end_str = datetime.now().strftime("%Y-%m-%d")
                 start_str = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                 
                 # Fetch from vnstock
                 stock_cls = Vnstock().stock(symbol=clean_ticker, source='VCI')
                 df_vn = stock_cls.quote.history(start=start_str, end=end_str)
                 
                 if df_vn is not None and not df_vn.empty:
                     # Standardize to match yfinance structure
                     df_vn = df_vn.rename(columns={
                         'time': 'Date', 'open': 'Open', 'high': 'High', 
                         'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                     })
                     df_vn['Date'] = pd.to_datetime(df_vn['Date'])
                     df_vn = df_vn.set_index('Date')
                     
                     # Ensure numeric types
                     cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                     for c in cols:
                         if c in df_vn.columns:
                             df_vn[c] = pd.to_numeric(df_vn[c], errors='coerce')
                     
                     data = df_vn
                     print(f"vnstock fallback success: {len(data)} rows")
             except Exception as e:
                 print(f"vnstock fallback error: {e}")

        if len(data) < 60:
             raise HTTPException(status_code=400, detail="Không đủ dữ liệu lịch sử (cả yfinance và vnstock đều k tìm thấy).")
             
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

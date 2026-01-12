from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import json
from datetime import datetime
import pytz

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# KHO DỮ LIỆU RAM
ORACLE_DATA_STORE = {
    "status": "waiting",
    "data": {}, 
    "rrg_cache": [],
    "last_updated": None
}

@app.get("/")
def read_root():
    return {"message": "Quant Server Active", "status": ORACLE_DATA_STORE["status"]}

# --- 1. NHẬN DỮ LIỆU TỪ COLAB ---
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        payload = await request.json()
        if "data" in payload: clean_data = payload["data"]
        else: clean_data = payload

        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        # Lấy giờ Việt Nam (UTC+7) cho chuẩn
        tz_VN = pytz.timezone('Asia/Ho_Chi_Minh') 
        ORACLE_DATA_STORE["last_updated"] = datetime.now(tz_VN).strftime("%H:%M %d/%m")
        
        # Tự tính RRG ngay lập tức
        calculate_rrg_internal(clean_data)
        
        return {"status": "success", "count": len(clean_data)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- HÀM TÌM BENCHMARK (LOGIC MỚI) ---
def get_benchmark_data(data):
    # Ưu tiên tìm ETF VN30 trước, nếu không có mới tìm các mã Index cũ
    # Colab gửi tên gì thì Server bắt tên đó
    for key in ["E1VFVN30.VN", "VNINDEX.VN", "^VNINDEX"]:
        if key in data:
            return key, data[key]
    return None, None

# --- HÀM TÍNH TOÁN NỘI BỘ ---
def calculate_pulse():
    if ORACLE_DATA_STORE["status"] != "ready":
        return {"score": 0, "status": "WARMUP ⏳", "timestamp": "Loading..."}

    try:
        data = ORACLE_DATA_STORE["data"]
        uptrend = 0
        total = 0
        
        # Lọc danh sách mã để tính độ rộng thị trường
        for t, p in data.items():
            # Bỏ qua các mã Index/ETF khi đếm số mã tăng
            if "INDEX" in t or "E1VFVN30" in t or len(p) < 20: continue
            
            # So sánh giá hiện tại với MA20
            if p[-1] > (sum(p[-20:])/20): uptrend += 1
            total += 1
        
        score = uptrend / total if total > 0 else 0.5
        state = "GREED 🐂" if score >= 0.55 else ("FEAR 🐻" if score <= 0.45 else "NEUTRAL 😐")
        
        # Lấy số liệu Benchmark (Ưu tiên VN30 ETF)
        bench_key, bench_prices = get_benchmark_data(data)
        
        vn_price = 0
        vn_change = 0
        
        if bench_prices and len(bench_prices) >= 2:
            vn_price = bench_prices[-1]
            vn_change = vn_price - bench_prices[-2]

        time_str = ORACLE_DATA_STORE["last_updated"]

        return {
            "score": round(score, 2),
            "sentiment_score": round(score, 2), # Legacy key
            "status": state,
            "market_status": state, # Legacy key
            "vnindex": round(vn_price, 2), # Giá này có thể là ~20.000 (ETF)
            "vnindex_price": round(vn_price, 2), # Legacy key
            "change": round(vn_change, 2),
            "vnindex_change": round(vn_change, 2), # Legacy key
            "timestamp": time_str
        }
    except: return {"score": 0, "status": "ERROR"}

def calculate_rrg_internal(data):
    try:
        rrg_list = []
        # Tìm Benchmark để so sánh RRG
        bench_key, bench_prices = get_benchmark_data(data)
        
        if not bench_prices: return # Không có benchmark thì thôi

        series_bench = pd.Series(bench_prices)
        
        for ticker, prices in data.items():
            if ticker == bench_key or len(prices) < 20: continue
            
            series_stock = pd.Series(prices)
            
            # Công thức RRG (JdK RS-Ratio)
            rs = 100 * (series_stock / series_bench)
            rs_ratio = (rs / rs.rolling(10).mean()) * 100
            rs_mom = (rs_ratio / rs_ratio.shift(1)) * 100
            
            if not np.isnan(rs_ratio.iloc[-1]):
                rrg_list.append({
                    "Ticker": ticker.replace(".VN", ""),
                    "Group": "VN30",
                    "RS_Ratio": round(rs_ratio.iloc[-1], 2),
                    "RS_Momentum": round(rs_mom.iloc[-1], 2)
                })
        ORACLE_DATA_STORE["rrg_cache"] = rrg_list
    except: pass

# --- 2. API ROUTING (OMNI-CHANNEL: GET & POST) ---
@app.api_route("/api/dashboard/sentiment", methods=["GET", "POST"])
def get_sentiment_fix(request: Request):
    return calculate_pulse()

@app.api_route("/api/market-pulse", methods=["GET", "POST"])
def get_pulse_fix(request: Request):
    return calculate_pulse()

@app.api_route("/api/dashboard/rrg", methods=["GET", "POST"])
def get_rrg_fix(request: Request):
    if ORACLE_DATA_STORE["rrg_cache"]:
        return ORACLE_DATA_STORE["rrg_cache"]
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

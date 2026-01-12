# FILE: backend/main.py (FINAL COMPATIBILITY VERSION)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import json

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
    "data": {}, # Chứa giá đóng cửa
    "rrg_cache": [], # Cache RRG tính sẵn
    "last_updated": None
}

@app.get("/")
def read_root():
    return {"message": "Quant Server is Awake!", "oracle": ORACLE_DATA_STORE["status"]}

# --- 1. NHẬN DỮ LIỆU TỪ COLAB (Universal Receiver) ---
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        payload = await request.json()
        if "data" in payload: clean_data = payload["data"]
        else: clean_data = payload

        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        ORACLE_DATA_STORE["last_updated"] = pd.Timestamp.now().isoformat()
        
        # Tự động tính RRG sơ bộ để lưu Cache (Phục vụ API RRG)
        calculate_rrg_internal(clean_data)
        
        print(f"✅ ORACLE UPDATED: {len(clean_data)} tickers")
        return {"status": "success", "count": len(clean_data)}
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"status": "error", "detail": str(e)}

# --- HÀM TÍNH RRG NỘI BỘ (Để phục vụ API cũ) ---
def calculate_rrg_internal(data):
    try:
        rrg_list = []
        # Tìm Benchmark
        bench_key = "VNINDEX.VN" if "VNINDEX.VN" in data else "^VNINDEX"
        if bench_key not in data: return
        
        bench_prices = pd.Series(data[bench_key])
        
        for ticker, prices in data.items():
            if ticker == bench_key or len(prices) < 20: continue
            
            # Tính toán RS Ratio & Momentum đơn giản
            p_series = pd.Series(prices)
            rs = 100 * (p_series / bench_prices)
            rs_ratio = (rs / rs.rolling(10).mean()) * 100
            rs_mom = (rs_ratio / rs_ratio.shift(1)) * 100
            
            if not np.isnan(rs_ratio.iloc[-1]):
                rrg_list.append({
                    "Ticker": ticker.replace(".VN", ""), # Bỏ đuôi VN cho đẹp
                    "Group": "VN30", # Mặc định
                    "RS_Ratio": round(rs_ratio.iloc[-1], 2),
                    "RS_Momentum": round(rs_mom.iloc[-1], 2)
                })
        ORACLE_DATA_STORE["rrg_cache"] = rrg_list
    except: pass

# --- 2. CÁC API TRẢ DỮ LIỆU CHO WEB (Routing đúng tên cũ) ---

# A. API MARKET PULSE (Web gọi /api/dashboard/sentiment)
@app.get("/api/dashboard/sentiment") 
def get_sentiment_old():
    return calculate_pulse()

@app.get("/api/market-pulse") # Cổng mới (dự phòng)
def get_sentiment_new():
    return calculate_pulse()

def calculate_pulse():
    if ORACLE_DATA_STORE["status"] != "ready":
        return {"score": 0, "status": "WARMUP ⏳"}

    try:
        data = ORACLE_DATA_STORE["data"]
        uptrend = 0
        total = 0
        for t, p in data.items():
            if "INDEX" in t or len(p) < 20: continue
            if p[-1] > (sum(p[-20:])/20): uptrend += 1
            total += 1
        
        score = uptrend / total if total > 0 else 0.5
        state = "GREED 🐂" if score >= 0.55 else ("FEAR 🐻" if score <= 0.45 else "NEUTRAL 😐")
        
        # Lấy VNINDEX
        vn_key = "VNINDEX.VN" if "VNINDEX.VN" in data else "^VNINDEX"
        vn_price = data[vn_key][-1] if vn_key in data else 0
        vn_change = vn_price - data[vn_key][-2] if vn_key in data and len(data[vn_key]) > 1 else 0

        return {"score": round(score, 2), "status": state, "vnindex": round(vn_price, 2), "change": round(vn_change, 2)}
    except: return {"score": 0, "status": "ERROR"}

# B. API RRG (Web gọi /api/dashboard/rrg)
@app.get("/api/dashboard/rrg")
def get_rrg_data():
    # Trả về dữ liệu RRG tính từ RAM
    if ORACLE_DATA_STORE["rrg_cache"]:
        return ORACLE_DATA_STORE["rrg_cache"]
    return [] # Trả về rỗng nếu chưa có, Web sẽ tự thử load CSV

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

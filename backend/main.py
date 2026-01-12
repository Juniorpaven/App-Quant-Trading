# FILE: backend/main.py (FINAL OMNI-CHANNEL VERSION)
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
    "data": {}, 
    "rrg_cache": [],
    "last_updated": None
}

@app.get("/")
def read_root():
    return {"message": "Quant Server is Awake!", "oracle": ORACLE_DATA_STORE["status"]}

# --- 1. NHẬN DỮ LIỆU TỪ COLAB ---
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        payload = await request.json()
        if "data" in payload: clean_data = payload["data"]
        else: clean_data = payload

        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        ORACLE_DATA_STORE["last_updated"] = pd.Timestamp.now().isoformat()
        
        # Tự động tính RRG sơ bộ lưu Cache
        calculate_rrg_internal(clean_data)
        
        print(f"✅ ORACLE UPDATED: {len(clean_data)} tickers")
        return {"status": "success", "count": len(clean_data)}
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {"status": "error", "detail": str(e)}

# --- HÀM LOGIC NỘI BỘ ---
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
        
        # Lấy VNINDEX (đã được Colab trá hình gửi sang)
        vn_key = "VNINDEX.VN" if "VNINDEX.VN" in data else "^VNINDEX"
        vn_price = data[vn_key][-1] if vn_key in data else 0
        vn_change = vn_price - data[vn_key][-2] if vn_key in data and len(data[vn_key]) > 1 else 0

        # Return SUPERSET of keys to satisfy all frontend versions
        return {
            "score": round(score, 2),
            "sentiment_score": round(score, 2), # Legacy key
            "status": state,
            "market_status": state, # Legacy key
            "vnindex": round(vn_price, 2),
            "vnindex_price": round(vn_price, 2), # Legacy key
            "change": round(vn_change, 2),
            "vnindex_change": round(vn_change, 2) # Legacy key
        }
    except: return {"score": 0, "status": "ERROR"}

def calculate_rrg_internal(data):
    try:
        rrg_list = []
        bench_key = "VNINDEX.VN" if "VNINDEX.VN" in data else "^VNINDEX"
        if bench_key not in data: return
        bench_prices = pd.Series(data[bench_key])
        
        for ticker, prices in data.items():
            if ticker == bench_key or len(prices) < 20: continue
            p_series = pd.Series(prices)
            rs = 100 * (p_series / bench_prices)
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

# --- 2. API TƯƠNG THÍCH (FIX LỖI 405) ---
# Dùng api_route với methods=["GET", "POST"] để chấp nhận mọi kiểu gọi

@app.api_route("/api/dashboard/sentiment", methods=["GET", "POST"])
def get_sentiment_compatibility(request: Request):
    return calculate_pulse()

@app.api_route("/api/market-pulse", methods=["GET", "POST"])
def get_pulse_compatibility(request: Request):
    return calculate_pulse()

@app.api_route("/api/dashboard/rrg", methods=["GET", "POST"])
def get_rrg_compatibility(request: Request):
    # Trả về dữ liệu RRG tính từ RAM
    if ORACLE_DATA_STORE["rrg_cache"]:
        return ORACLE_DATA_STORE["rrg_cache"]
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

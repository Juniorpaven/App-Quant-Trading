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
    "last_updated": None
}

@app.get("/")
def read_root():
    return {"message": "Quant Server is Awake!", "oracle": ORACLE_DATA_STORE["status"]}

# --- ĐÂY LÀ PHẦN SỬA LỖI 422 QUAN TRỌNG NHẤT ---
# Thay vì dùng Pydantic Model cứng nhắc, ta dùng Request để nhận mọi thứ
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        # 1. Đọc dữ liệu thô bất chấp định dạng
        payload = await request.json()
        
        # 2. Kiểm tra xem có key "data" không, nếu không thì lấy toàn bộ
        if "data" in payload:
            clean_data = payload["data"]
        else:
            clean_data = payload

        # 3. Lưu vào RAM
        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        ORACLE_DATA_STORE["last_updated"] = pd.Timestamp.now().isoformat()
        
        print(f"✅ ORACLE UPDATED: Received {len(clean_data)} tickers")
        return {"status": "success", "count": len(clean_data)}
        
    except Exception as e:
        print(f"❌ ERROR UPLOAD: {e}")
        return {"status": "error", "detail": str(e)}

# API TÍNH TOÁN MARKET PULSE (Dựa trên dữ liệu RAM)
@app.get("/api/market-pulse")
def get_market_pulse():
    if ORACLE_DATA_STORE["status"] != "ready":
        return {"score": 0, "status": "WARMUP ⏳", "message": "Waiting for Colab..."}

    try:
        data_cache = ORACLE_DATA_STORE["data"]
        
        # LOGIC TÍNH TOÁN ĐƠN GIẢN HÓA
        uptrend_count = 0
        total_count = 0
        
        for ticker, prices in data_cache.items():
            if ticker == "VNINDEX.VN" or ticker == "^VNINDEX": continue
            if not isinstance(prices, list) or len(prices) < 20: continue
            
            # Lấy giá mới nhất và MA20
            latest_price = prices[-1]
            ma20 = sum(prices[-20:]) / 20
            
            if latest_price > ma20:
                uptrend_count += 1
            total_count += 1
            
        score = uptrend_count / total_count if total_count > 0 else 0.5
        
        state = "NEUTRAL 😐"
        if score >= 0.55: state = "GREED 🐂"
        elif score <= 0.45: state = "FEAR 🐻"
        
        # Lấy chỉ số VNINDEX
        vn_price = 0
        vn_change = 0
        vn_key = "^VNINDEX" if "^VNINDEX" in data_cache else "VNINDEX.VN"
        
        if vn_key in data_cache:
            idx_list = data_cache[vn_key]
            if len(idx_list) >= 2:
                vn_price = idx_list[-1]
                vn_change = vn_price - idx_list[-2]

        return {
            "score": round(score, 2),
            "status": state,
            "vnindex": round(vn_price, 2),
            "change": round(vn_change, 2)
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

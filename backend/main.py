# FILE: backend/main.py (VERSION 7.0 - FULL RESTORE)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import json
from datetime import datetime
import pytz

app = FastAPI()

# Cấu hình CORS để Web không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# KHO DỮ LIỆU RAM (Lưu trữ mọi thứ Colab gửi sang)
ORACLE_DATA_STORE = {
    "status": "waiting",
    "data": {},        # Dữ liệu giá đóng cửa
    "rrg_cache": [],   # Kết quả RRG đã tính
    "last_updated": None
}

@app.get("/")
def read_root():
    return {"message": "Quant Server V7.0 Active", "status": ORACLE_DATA_STORE["status"]}

# ==========================================================
# 1. CỔNG NHẬN DỮ LIỆU TỪ COLAB (BƠM MÁU)
# ==========================================================
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        payload = await request.json()
        # Linh hoạt lấy data dù có vỏ bọc hay không
        if "data" in payload: clean_data = payload["data"]
        else: clean_data = payload

        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        
        # Lấy giờ VN
        tz_VN = pytz.timezone('Asia/Ho_Chi_Minh')
        ORACLE_DATA_STORE["last_updated"] = datetime.now(tz_VN).strftime("%H:%M %d/%m")
        
        # Tính ngay RRG để lưu cache
        calculate_rrg_internal(clean_data)
        
        print(f"✅ ORACLE RESTORED: {len(clean_data)} tickers loaded.")
        return {"status": "success", "count": len(clean_data)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ==========================================================
# 2. CÁC API PHỤC VỤ WEB (KHÔI PHỤC LẠI TẤT CẢ)
# ==========================================================

# A. MARKET PULSE (Đồng hồ đo tâm lý)
@app.api_route("/api/dashboard/sentiment", methods=["GET", "POST"])
def get_sentiment(request: Request): return calculate_pulse()

@app.api_route("/api/market-pulse", methods=["GET", "POST"])
def get_pulse(request: Request): return calculate_pulse()

# B. RRG CHART (Biểu đồ luân chuyển)
@app.api_route("/api/dashboard/rrg", methods=["GET", "POST"])
def get_rrg(request: Request):
    if ORACLE_DATA_STORE["rrg_cache"]:
        return ORACLE_DATA_STORE["rrg_cache"]
    return []

# C. FUNDAMENTAL SNAPSHOT (Khôi phục & dùng dữ liệu RAM)
@app.api_route("/api/dashboard/fundamentals", methods=["GET", "POST"])
async def get_fundamentals(request: Request):
    try:
        # Lấy ticker từ Request (GET hoặc POST)
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "HPG")
        else:
            ticker = request.query_params.get("ticker", "HPG")

        # Chuẩn hóa tên (thêm .VN nếu thiếu)
        if hasattr(ticker, 'endswith') and not ticker.endswith(".VN") and ticker != "^VNINDEX" and "E1VFVN30" not in ticker:
            ticker += ".VN"

        data = ORACLE_DATA_STORE["data"]
        
        # Nếu không có dữ liệu -> Trả về N/A
        if ticker not in data:
            return {
                "ticker": ticker, "current_price": 0, "change": 0, "pct_change": 0,
                "pe": "N/A", "roe": "N/A", "signal": "No Data"
            }

        prices = data[ticker]
        if len(prices) < 2:
            return {"ticker": ticker, "current_price": prices[-1], "change": 0}

        curr = prices[-1]
        prev = prices[-2]
        change = curr - prev
        pct = (change / prev) * 100

        return {
            "ticker": ticker,
            "current_price": curr,
            "change": round(change, 2),
            "pct_change": round(pct, 2),
            "pe": "Updating...", # Colab chưa gửi P/E, để tạm placeholder
            "roe": "Updating...",
            "signal": "Neutral"
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# D. CHART API (Vẽ biểu đồ nhỏ)
@app.api_route("/api/dashboard/chart", methods=["GET", "POST"])
async def get_chart(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "HPG")
        else:
            ticker = request.query_params.get("ticker", "HPG")
            
        if ticker and isinstance(ticker, str) and not ticker.endswith(".VN"):
            ticker += ".VN"
        
        data = ORACLE_DATA_STORE["data"]
        if ticker in data:
            # Trả về 30 phiên gần nhất để vẽ chart
            recent_prices = data[ticker][-30:]
            return {
                "ticker": ticker,
                "prices": recent_prices,
                "labels": [f"T{i}" for i in range(len(recent_prices))]
            }
        return {"prices": [], "labels": []}
    except: return {"prices": [], "labels": []}

# E. AI ORACLE (Khôi phục logic tư vấn đơn giản)
@app.api_route("/api/ask-ai", methods=["GET", "POST"])
async def ask_ai(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "")
        else:
            ticker = request.query_params.get("ticker", "")

        if hasattr(ticker, 'endswith') and not ticker.endswith(".VN"): ticker += ".VN"
        data = ORACLE_DATA_STORE["data"]

        if ticker not in data or len(data[ticker]) < 20:
            return {"answer": f"Tôi chưa có đủ dữ liệu về mã {ticker} để tư vấn."}

        # Logic AI đơn giản: So sánh giá với MA20
        prices = data[ticker]
        last_price = prices[-1]
        ma20 = sum(prices[-20:]) / 20
        trend = "TĂNG 📈" if last_price > ma20 else "GIẢM 📉"
        
        return {
            "answer": f"🤖 Phân tích {ticker}:\n- Giá hiện tại: {last_price:,.0f}\n- Xu hướng ngắn hạn: {trend}\n- Vị thế: Đang {'nằm trên' if last_price > ma20 else 'nằm dưới'} đường trung bình 20 phiên."
        }
    except:
        return {"answer": "Lỗi xử lý AI."}

# ==========================================================
# 3. LOGIC TÍNH TOÁN (INTERNAL)
# ==========================================================
def calculate_pulse():
    if ORACLE_DATA_STORE["status"] != "ready":
        return {"score": 0, "status": "WARMUP ⏳", "timestamp": "Loading..."}

    try:
        data = ORACLE_DATA_STORE["data"]
        uptrend = 0
        total = 0
        for t, p in data.items():
            if "INDEX" in t or "E1VFVN30" in t or len(p) < 20: continue
            if p[-1] > (sum(p[-20:])/20): uptrend += 1
            total += 1
        
        score = uptrend / total if total > 0 else 0.5
        state = "GREED 🐂" if score >= 0.55 else ("FEAR 🐻" if score <= 0.45 else "NEUTRAL 😐")
        
        # Tìm Benchmark
        vn_price = 0
        vn_change = 0
        for k in ["E1VFVN30.VN", "VNINDEX.VN", "^VNINDEX"]:
            if k in data and len(data[k]) > 1:
                vn_price = data[k][-1]
                vn_change = vn_price - data[k][-2]
                break

        # Return SUPERSET of keys to satisfy all frontend versions
        return {
            "score": round(score, 2),
            "sentiment_score": round(score, 2), # Legacy key
            "status": state,
            "market_status": state, # Legacy key
            "vnindex": round(vn_price, 2), # Giá này có thể là ~20.000 (ETF)
            "vnindex_price": round(vn_price, 2), # Legacy key
            "change": round(vn_change, 2),
            "vnindex_change": round(vn_change, 2), # Legacy key
            "timestamp": ORACLE_DATA_STORE["last_updated"]
        }
    except: return {"score": 0, "status": "ERROR"}

def calculate_rrg_internal(data):
    try:
        rrg_list = []
        bench_prices = None
        for k in ["E1VFVN30.VN", "VNINDEX.VN", "^VNINDEX"]:
            if k in data: 
                bench_prices = pd.Series(data[k])
                break
        
        if bench_prices is None: return

        for ticker, prices in data.items():
            if "INDEX" in ticker or "E1VFVN30" in ticker or len(prices) < 20: continue
            p = pd.Series(prices)
            rs = 100 * (p / bench_prices)
            rs_ratio = (rs / rs.rolling(10).mean()) * 100
            rs_mom = (rs_ratio / rs_ratio.shift(1)) * 100
            
            if not np.isnan(rs_ratio.iloc[-1]):
                rrg_list.append({
                    "Ticker": ticker.replace(".VN", ""), "Group": "VN30",
                    "RS_Ratio": round(rs_ratio.iloc[-1], 2), "RS_Momentum": round(rs_mom.iloc[-1], 2)
                })
        ORACLE_DATA_STORE["rrg_cache"] = rrg_list
    except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

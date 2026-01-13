# FILE: backend/main.py (STABILITY UPDATE - BULLETPROOF)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import json
from datetime import datetime
import pytz
import yfinance as yf

app = FastAPI()

# Cấu hình CORS mở rộng tối đa
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
    return {"message": "Quant Server Stability V7.1 Active", "status": ORACLE_DATA_STORE["status"]}

# --- HELPER: Valid Ticker Check (Chống Crash) ---
def clean_ticker(ticker):
    if not ticker or not isinstance(ticker, str):
        return "HPG.VN" # Default safe
    ticker = ticker.upper().strip()
    if not ticker.endswith(".VN") and ticker != "^VNINDEX" and "E1VFVN30" not in ticker:
        ticker += ".VN"
    return ticker

# --- 1. NHẬN DỮ LIỆU TỪ COLAB ---
@app.post("/api/upload-oracle")
async def upload_oracle(request: Request):
    try:
        payload = await request.json()
        if "data" in payload: clean_data = payload["data"]
        else: clean_data = payload

        ORACLE_DATA_STORE["data"] = clean_data
        ORACLE_DATA_STORE["status"] = "ready"
        
        tz_VN = pytz.timezone('Asia/Ho_Chi_Minh')
        ORACLE_DATA_STORE["last_updated"] = datetime.now(tz_VN).strftime("%H:%M %d/%m")
        
        calculate_rrg_internal(clean_data)
        return {"status": "success", "count": len(clean_data)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- 2. CÁC API PHỤC VỤ WEB ---

# A. MARKET PULSE (Đa dạng key, chống cache)
@app.api_route("/api/dashboard/sentiment", methods=["GET", "POST"])
def get_sentiment(response: Response): 
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return calculate_pulse()

@app.api_route("/api/market-pulse", methods=["GET", "POST"])
def get_pulse(response: Response): 
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return calculate_pulse()

# B. RRG CHART
@app.api_route("/api/dashboard/rrg", methods=["GET", "POST"])
def get_rrg(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    if ORACLE_DATA_STORE["rrg_cache"]:
        return ORACLE_DATA_STORE["rrg_cache"]
    return []

# C. FUNDAMENTAL SNAPSHOT (Fix Crash)
@app.api_route("/api/dashboard/fundamentals", methods=["GET", "POST"])
async def get_fundamentals(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "HPG")
        else:
            ticker = request.query_params.get("ticker", "HPG")

        ticker = clean_ticker(ticker)
        data = ORACLE_DATA_STORE["data"]
        
        if ticker in data and len(data[ticker]) >= 2:
            prices = data[ticker]
        else:
            # Fallback Fetch
            try:
                # Fetch minimal history for change calc
                df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
                if not df.empty:
                    try: p = df.xs(ticker, level=1, axis=1)['Close']
                    except: p = df['Close']
                    prices = p.dropna().tolist()
            except: pass

        if len(prices) < 2:
            return {"ticker": ticker, "current_price": 0, "change": 0}
        curr = prices[-1]
        prev = prices[-2]
        change = curr - prev
        pct = (change / prev) * 100

        return {
            "ticker": ticker,
            "current_price": curr,
            "change": round(change, 2),
            "pct_change": round(pct, 2),
            "pe": "Updating...", "roe": "Updating...", "signal": "Neutral"
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# D. CHART API (Fix Crash + On-the-fly Fetch)
@app.api_route("/api/dashboard/chart", methods=["GET", "POST"])
async def get_chart(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "HPG")
        else:
            ticker = request.query_params.get("ticker", "HPG")
            
        ticker = clean_ticker(ticker)
        data = ORACLE_DATA_STORE["data"]
        
        recent_prices = []
        
        # 1. Try RAM
        if ticker in data and len(data[ticker]) >= 30:
            recent_prices = data[ticker][-30:]
        else:
            # 2. Fallback: Fetch Live from Yahoo
            try:
                print(f"Fetching live for {ticker}...")
                df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
                if not df.empty:
                    try: prices = df.xs(ticker, level=1, axis=1)['Close']
                    except: prices = df['Close']
                    
                    recent_prices = prices.dropna().tolist()[-30:]
            except Exception as e:
                print(f"Live fetch fail: {e}")

        if recent_prices:
            return {
                "ticker": ticker,
                "prices": recent_prices,
                "labels": [f"T{i}" for i in range(len(recent_prices))]
            }
            
        return {"prices": [], "labels": []}
    except: return {"prices": [], "labels": []}

# E. AI ORACLE (Fix Crash)
@app.api_route("/api/ask-ai", methods=["GET", "POST"])
async def ask_ai(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
            ticker = body.get("ticker", "")
        else:
            ticker = request.query_params.get("ticker", "")

        ticker = clean_ticker(ticker)
        data = ORACLE_DATA_STORE["data"]

        if ticker not in data or len(data[ticker]) < 20:
            return {"answer": f"Tôi chưa có đủ dữ liệu về mã {ticker} để tư vấn."}

        prices = data[ticker]
        last_price = prices[-1]
        ma20 = sum(prices[-20:]) / 20
        trend = "TĂNG 📈" if last_price > ma20 else "GIẢM 📉"
        
        return {
            "answer": f"🤖 Phân tích {ticker}:\n- Giá hiện tại: {last_price:,.0f}\n- Xu hướng ngắn hạn: {trend}\n- Vị thế: Đang {'nằm trên' if last_price > ma20 else 'nằm dưới'} đường trung bình 20 phiên."
        }
    except:
        return {"answer": "Lỗi xử lý AI."}

# --- INTERNAL LOGIC ---
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
        
        vn_price = 0
        vn_change = 0
        for k in ["E1VFVN30.VN", "VNINDEX.VN", "^VNINDEX"]:
            if k in data and len(data[k]) > 1:
                vn_price = data[k][-1]
                vn_change = vn_price - data[k][-2]
                break

        time_str = ORACLE_DATA_STORE["last_updated"]
        
        return {
            "score": round(score, 2), "sentiment_score": round(score, 2),
            "status": state, "market_status": state,
            "vnindex": round(vn_price, 2), "vnindex_price": round(vn_price, 2),
            "change": round(vn_change, 2), "vnindex_change": round(vn_change, 2),
            "timestamp": time_str,
            "last_updated": time_str,  # Dự phòng
            "updatedAt": time_str,     # Dự phòng
            "date": time_str           # Dự phòng
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

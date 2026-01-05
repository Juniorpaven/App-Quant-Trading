
import sys
import os
import pandas as pd
import json
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# Mocking the functions from main.py for isolation testing

def get_ohlcv_smart(ticker, period="1y"):
    """
    Fetch OHLCV data using Yahoo Finance first, fallback to Vnstock if failed.
    """
    # 1. Try Yahoo Finance
    yf_ticker = ticker.strip().upper()
    if "-" not in yf_ticker and "^" not in yf_ticker and ".VN" not in yf_ticker:
        yf_ticker += ".VN"
        
    print(f"Chart: Fetching {yf_ticker} via Yahoo...")
    try:
        # Using 6mo to match potential recent changes or just 1y default
        df = yf.download(yf_ticker, period=period, progress=False, auto_adjust=True)
        # Handle MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
             # Try to get the ticker level if it exists
            if yf_ticker in df.columns.levels[1]:
                 df = df.xs(yf_ticker, level=1, axis=1)
            elif yf_ticker.replace('.VN', '') in df.columns.levels[1]:
                 df = df.xs(yf_ticker.replace('.VN', ''), level=1, axis=1)
        
        # Check basic columns
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not df.empty:
            # Check if columns are present (sometimes Yahoo returns 'Adj Close', etc)
            # If MultiIndex issue persists or simple logic
            print("Columns:", df.columns)
            
            # Simple check
            if all(col in df.columns for col in required):
                print("Chart: Yahoo Success.")
                return df[required]
    except Exception as e:
        print(f"Chart: Yahoo failed: {e}")

    return pd.DataFrame()

def calculate_volume_profile(df, price_col='Close', vol_col='Volume', bins=50):
    if len(df) < 2: return pd.DataFrame(), 0
    import numpy as np
    
    # 1. Xác định biên độ giá toàn bộ giai đoạn
    min_price = df['Low'].min()
    max_price = df['High'].max()
    
    # 2. Chia nhỏ mức giá thành các giỏ (bins)
    price_range = np.linspace(min_price, max_price, bins)
    
    # 3. Tính tổng volume cho từng mức giá
    close_prices = df[price_col].values
    volumes = df[vol_col].values
    
    hist, bin_edges = np.histogram(close_prices, bins=price_range, weights=volumes)
    
    # 4. Tìm POC (Point of Control)
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
    
    print(f"VP Data Rows: {len(vp_df)}")
    print(f"POC Price: {poc_price}")

    # Tạo biểu đồ chính (Nến)
    fig = go.Figure()
    
    # 1. Vẽ Nến
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name=f'{ticker_name} Price'
    ))
    
    return fig

def test_chart_generation():
    ticker = "HPG"
    print(f"Testing Chart for {ticker}...")
    
    df = get_ohlcv_smart(ticker)
    
    if df.empty:
        print("ERROR: getting empty dataframe")
        return
        
    print(f"Got DataFrame: {len(df)} rows")
    print(df.head())
    
    try:
        fig = plot_candlestick_with_vp(df, ticker)
        json_str = fig.to_json()
        data_dict = json.loads(json_str)
        
        print("Successfully generated Plotly JSON")
        print("Keys in JSON:", data_dict.keys())
        if 'data' in data_dict:
             print("Traces:", len(data_dict['data']))
    except Exception as e:
        print(f"Error producing chart: {e}")

if __name__ == "__main__":
    test_chart_generation()

---
description: Quy trình tạo dữ liệu RRG thủ công bằng Google Colab (Backup khi Server lỗi)
---

# Quy trình Fail-safe: Tạo Snapshot RRG từ Google Colab

Tài liệu này hướng dẫn cách sử dụng Google Colab để tính toán dữ liệu RRG và tạo file CSV snapshot.
Sử dụng khi Server API gặp sự cố hoặc cần phân tích dữ liệu tùy chỉnh.

## Bước 1: Mở Google Colab
1. Truy cập [Google Colab](https://colab.research.google.com/).
2. Tạo một Notebook mới (New Notebook).

## Bước 2: Dán Code Xử Lý
Copy toàn bộ đoạn code sau vào ô code đầu tiên của Colab và bấm nút Play (▶️).

```python
# ==============================================================================
# MÁY TÍNH TOÁN RRG & XUẤT CSV (PHIÊN BẢN CHỐNG LỖI YAHOO)
# ==============================================================================

# 1. CÀI ĐẶT & KẾT NỐI DRIVE
!pip install yfinance pandas numpy --quiet
import yfinance as yf
import pandas as pd
import numpy as np
import io
from google.colab import auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Xác thực người dùng (Làm theo hướng dẫn trên màn hình Colab)
print("🔑 Đang xác thực Google Drive...")
try:
    auth.authenticate_user()
except:
    print("⚠️ Bỏ qua xác thực Drive (Chỉ tải file về máy)")

# 2. DANH SÁCH MÃ & CẤU HÌNH
print("⏳ Đang chuẩn bị danh sách mã...")

sector_map = {
    "Ngan_hang": ["VCB", "BID", "CTG", "TCB", "VPB", "MBB", "ACB", "STB", "HDB", "VIB", "TPB", "SHB", "SSB", "LPB", "EIB", "MSB", "OCB"],
    "Thep": ["HPG", "HSG", "NKG", "VGS", "TVN", "TLH"],
    "Bat_dong_san": ["VHM", "VIC", "VRE", "NVL", "PDR", "DIG", "CEO", "DXG", "KDH", "NAM", "KBC", "SZC", "IDC"],
    "Chung_khoan": ["SSI", "VND", "VCI", "HCM", "SHS", "MBS", "FTS", "BSI", "CTS", "VIX"],
    "Ban_le_Cong_nghe": ["MWG", "FPT", "FRT", "DGW", "PNJ", "MSN", "VNM", "SAB"],
    "Dau_khi": ["GAS", "PLX", "PVD", "PVS", "BSR", "POW", "GEG", "NT2"],
    "VN30": ["ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG","MBB","MSN","MWG","PLX","POW","SAB","SHB","SSB","SSI","STB","TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM","VPB","VRE"]
}

all_tickers = list(set([t for val in sector_map.values() for t in val]))
yf_tickers = [t + ".VN" for t in all_tickers]

# 3. CHIẾN THUẬT TẢI BENCHMARK (ĐA LỚP)
print("🛡️ Đang tìm Benchmark an toàn...")
benchmark_data = None
benchmark_name = ""
fallback_benchmarks = ["^VNINDEX", "VNINDEX.VN", "E1VFVN30.VN"]

for bm in fallback_benchmarks:
    try:
        print(f"   -> Thử tải: {bm}...")
        bm_df = yf.download(bm, period="1y", interval="1d", auto_adjust=True, progress=False)
        if not bm_df.empty and len(bm_df) > 100:
            if isinstance(bm_df.columns, pd.MultiIndex):
                try: bm_close = bm_df.xs(bm, level=1, axis=1)['Close']
                except: bm_close = bm_df['Close']
            else:
                bm_close = bm_df['Close']
            benchmark_data = bm_close
            benchmark_name = bm
            print(f"✅ Đã chốt Benchmark: {bm}")
            break
    except: continue

if benchmark_data is None:
    print("❌ LỖI: Không tải được Benchmark.")
else:
    # 4. TẢI CỔ PHIẾU & TÍNH TOÁN
    print(f"📥 Đang tải {len(yf_tickers)} mã cổ phiếu...")
    try:
        stock_data = yf.download(yf_tickers, period="1y", interval="1d", auto_adjust=True, group_by='ticker', threads=False, progress=False)
        rrg_rows = []
        
        for t in all_tickers:
            full_t = t + ".VN"
            try:
                if full_t in stock_data.columns.levels[0]: price = stock_data[full_t]['Close']
                else: continue
            except: continue

            if price.isnull().all() or len(price) < 10: continue

            common_index = price.index.intersection(benchmark_data.index)
            if len(common_index) < 10: continue

            price_aligned = price.loc[common_index]
            bench_aligned = benchmark_data.loc[common_index]

            # CÔNG THỨC RRG
            rs = 100 * (price_aligned / bench_aligned)
            rs_ratio = (rs / rs.rolling(10).mean()) * 100
            rs_momentum = (rs_ratio / rs_ratio.shift(1)) * 100

            rrg_rows.append({
                "Ticker": t,
                "Group": next((g for g, l in sector_map.items() if t in l), "Khac"),
                "RS_Ratio": round(rs_ratio.iloc[-1], 2),
                "RS_Momentum": round(rs_momentum.iloc[-1], 2)
            })

        # 5. XUẤT CSV
        if rrg_rows:
            df_final = pd.DataFrame(rrg_rows)[['Ticker', 'Group', 'RS_Ratio', 'RS_Momentum']]
            filename = "rrg_snapshot.csv"
            df_final.to_csv(filename, index=False)
            print(f"✅ ĐÃ TẠO FILE: {filename}")
            
            # Tải về máy local (nếu không dùng Drive)
            try:
                from google.colab import files
                files.download(filename)
                print("⬇️ Đang tải file về máy tính...")
            except:
                print("⚠️ Hãy tải thủ công từ menu Files bên trái.")
        else:
            print("❌ Không tính được mã nào.")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
```

## Bước 3: Nạp vào Web App
1. Sau khi code chạy xong, file `rrg_snapshot.csv` sẽ tự động được tải về máy tính của bạn.
2. Mở Web App Quant Trading -> Mục "Quant Cockpit".
3. Bấm nút "📂 Nạp File Snapshot (RRG)".
4. Chọn file CSV vừa tải về.

## Kết quả
- Biểu đồ RRG sẽ hiện ra ngay lập tức.
- Chỉ số Smart Pulse sẽ được tính toán lại dựa trên dữ liệu trong file CSV này (Chế độ Manual - Không có MA200 Filter).

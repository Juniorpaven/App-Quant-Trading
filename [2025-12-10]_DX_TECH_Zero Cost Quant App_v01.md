
# 2025-12-10_DX_TECH_Zero Cost Quant App_v01

This document outlines the strategy for deploying the Quant Trading Application using a **Zero-Cost Strategy**, leveraging free data sources and hosting tiers.

## 1. Zero-Cost Data Strategy (Chiến lược Dữ liệu Miễn phí)

### Thành phần Dữ liệu

1. **Giá Chứng khoán (History & EOD)**:
    * **Nguồn**: `yfinance` (Proxy cho Yahoo Finance API).
    * **Mục đích**: Cung cấp dữ liệu lịch sử và cuối ngày để chạy mô hình NTF.
    * **Hạn chế**: Độ trễ có thể >= 15 phút. Không dùng cho High-Frequency Trading.
    * **Triển khai**: Backend sẽ tự động tải dữ liệu khi có yêu cầu từ Frontend.

2. **Dữ liệu Cơ bản (Sector/Group)**:
    * **Nguồn**: File tĩnh (Static CSV/JSON).
    * **Mục đích**: Phân loại tài sản vào các nhóm ngành để chạy OPS Group Sparsity.
    * **Triển khai**: Lưu trữ trực tiếp trong Repository.

### Chiến lược Tối ưu (Caching)

Để tránh vượt quá giới hạn gọi API (Rate Limits) của các bên thứ ba (Yahoo Finance, Alpha Vantage), chúng ta áp dụng cơ chế **In-Memory Caching**.

* **Cơ chế**: Dữ liệu giá sau khi tải về sẽ được lưu vào RAM của Server.
* **Thời gian tồn tại (TTL)**: 4 giờ.
* **Lợi ích**:
  * Giảm số lần gọi API ra ngoài.
  * Tăng tốc độ phản hồi cho người dùng (nếu dữ liệu đã có trong Cache).
  * Phù hợp với môi trường Serverless (Render Free Tier) khi server còn sống.

## 2. Updated Backend Logic

Backend (`main.py`) đã được nâng cấp để hỗ trợ:

* **YFinance Integration**: Tích hợp module `yfinance` để tải dữ liệu thực tế.
* **Endpoint Mới**: `/api/run-ntf-engine` chấp nhận danh sách Tickers (ví dụ: `["AAPL", "GOOGL", "MSFT"]`) thay vì phải truyền toàn bộ mảng giá.
* **Backward Compatibility**: Vẫn giữ endpoint cũ `/api/ntf/momentum` cho các trường hợp kiểm thử thủ công.

### Requirements (`backend/requirements.txt`)

Yêu cầu đã được cập nhật để Render cài đặt:

```txt
fastapi
uvicorn
pandas
numpy
yfinance
networkx
```

## 3. Deployment Steps (Zero Cost)

### Backend: Render.com (Free Tier)

1. Push code lên GitHub.
2. Tạo Web Service mới trên Render.
3. Kết nối với Repo.
4. Build Command: `pip install -r backend/requirements.txt`
5. Start Command: `python backend/main.py`
6. **Lưu ý**: Server Free sẽ tự động "ngủ" (Spin down) sau 15 phút không hoạt động. Request đầu tiên sau đó sẽ mất khoảng 50s để khởi động lại.

### Frontend: Vercel (Hobby Plan)

1. Push code lên GitHub.
2. Tạo Project mới trên Vercel.
3. Set `Root Directory` là `frontend`.
4. Set Environment Variable `VITE_API_URL` bằng URL của Render Backend.
5. Deploy.

## 4. Usage Flow (Luồng Sử Dụng Mới)

1. Người dùng nhập mã chứng khoán trên Frontend (ví dụ: `SPY`, `IWM`, `TLT`).
2. Frontend gọi `/api/run-ntf-engine`.
3. Backend kiểm tra Cache. Nếu chưa có -> Gọi `yfinance`.
4. Backend tính toán Momentum Spillover bằng NTF Engine.
5. Kết quả trả về cho Frontend để hiển thị.

---
*Created by Antigravity AI Assistant on 2025-12-10.*

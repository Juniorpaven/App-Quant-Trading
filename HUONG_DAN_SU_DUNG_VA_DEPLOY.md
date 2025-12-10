
# Hướng Dẫn Sử Dụng & Triển Khai Web App Quant Trading

Tài liệu này hướng dẫn chi tiết cách chạy ứng dụng trên máy cá nhân (Localhost) và cách đưa ứng dụng lên môi trường Internet (Deployment).

---

## Phần 1: Hướng Dẫn Chạy Local (Trên máy tính cá nhân)

### 1. Yêu cầu cài đặt

Đảm bảo máy tính của bạn đã cài đặt các công cụ sau:

- **Python 3.8+**: [Tải về](https://www.python.org/downloads/)
- **Node.js 16+**: [Tải về](https://nodejs.org/)
- **Git**: [Tải về](https://git-scm.com/)

### 2. Cấu trúc dự án

Dự án bao gồm 2 phần chính:

- **Backend (Python/FastAPI)**: Xử lý logic tính toán (NTF, OPS). Chạy mặc định port `8000`.
- **Frontend (React/Vite)**: Giao diện người dùng. Chạy mặc định port `5173`.

### 3. Khởi chạy Backend

Mở một cửa sổ Terminal (Command Prompt/PowerShell) tại thư mục `quant_trading_app/backend`:

```bash
# Cài đặt các thư viện cần thiết (chỉ cần làm lần đầu)
pip install fastapi uvicorn pandas numpy

# Chạy server
python main.py
```

*Dấu hiệu thành công:* Bạn thấy thông báo `Uvicorn running on http://0.0.0.0:8000`.

### 4. Khởi chạy Frontend

Mở một cửa sổ Terminal **khác** tại thư mục `quant_trading_app/frontend`:

```bash
# Cài đặt các thư viện cần thiết (chỉ cần làm lần đầu)
npm install

# Chạy giao diện phát triển
npm run dev
```

*Dấu hiệu thành công:* Bạn thấy thông báo `Local: http://localhost:5173/`.

### 5. Sử dụng

- Truy cập trình duyệt tại địa chỉ: `http://localhost:5173/`
- **Nút "Check Backend Connectivity"**: Kiểm tra xem Frontend có kết nối được với Backend không.
- **Nút "Run NTF Engine"**: Chạy thử mô hình Network Trend Following với dữ liệu mẫu và hiển thị kết quả Momentum.

---

## Phần 2: Hướng Dẫn Đưa Lên Internet (Deployment)

Để ứng dụng chạy online 24/7, chúng ta sẽ cần deploy Backend và Frontend lên các dịch vụ đám mây (Cloud). Dưới đây là cách sử dụng các dịch vụ miễn phí/giá rẻ phổ biến.

### Bước 1: Chuẩn bị Code

Đẩy toàn bộ code của bạn lên **GitHub** (hoặc GitLab).

1. Tạo repository mới trên GitHub.
2. Commit và Push code lên đó.

### Bước 2: Deploy Backend (Ví dụ dùng Render.com)

**Render** hỗ trợ chạy Python Web App rất tốt.

1. Đăng ký tài khoản tại [Render.com](https://render.com/).
2. Chọn **New +** -> **Web Service**.
3. Kết nối với GitHub Repository của bạn.
4. Cấu hình:
   - **Root Directory**: `backend` (Rất quan trọng, vì code backend nằm trong thư mục này).
   - **Build Command**: `pip install -r requirements.txt` (Bạn cần tạo file `requirements.txt` liệt kê các thư viện: fastapi, uvicorn, pandas, numpy).
   - **Start Command**: `python main.py`
5. Nhấn **Deploy**.
6. Sau khi xong, Render sẽ cấp cho bạn một URL (ví dụ: `https://quant-backend.onrender.com`). **Lưu lại URL này.**

### Bước 3: Deploy Frontend (Ví dụ dùng Vercel)

**Vercel** tối ưu cho các ứng dụng React/Vite.

1. Đăng ký tài khoản tại [Vercel.com](https://vercel.com/).
2. Chọn **Add New...** -> **Project**.
3. Import GitHub Repository của bạn.
4. Cấu hình:
   - **Root Directory**: Chọn `frontend`.
   - **Framework Preset**: Vite.
   - **Environment Variables** (Biến môi trường):
     - Tên: `VITE_API_URL`
     - Giá trị: URL của Backend bạn vừa deploy ở Bước 2 (vd: `https://quant-backend.onrender.com` - *không có dấu gạch chéo cuối cùng*).
5. Nhấn **Deploy**.
6. Vercel sẽ cấp cho bạn một domain (ví dụ: `https://quant-frontend.vercel.app`).

### Bước 4: Cập nhật Backend (CORS)

Do Domain Frontend đã thay đổi (không còn là localhost), bạn cần cập nhật Backend để cho phép Domain mới này gọi API.

1. Mở file `backend/main.py`.
2. Tìm đoạn `origins = [...]`.
3. Thêm Domain Frontend của bạn vào danh sách:

   ```python
   origins = [
       "http://localhost:5173",
       "https://quant-frontend.vercel.app", # Thêm dòng này
   ]
   ```

4. Commit và Push code lên GitHub.
5. Render sẽ tự động cập nhật Backend.

### Hoàn tất

Giờ đây bạn có thể truy cập vào đường dẫn Frontend (Vercel) từ bất kỳ đâu trên Internet để sử dụng ứng dụng.



# HƯỚNG DẪN ĐẨY CODE LÊN GITHUB & DEPLOY (RENDER + VERCEL)

Tài liệu này hướng dẫn chi tiết từ A-Z cách đưa code từ máy tính của bạn lên Internet để chạy online.

---

## PHẦN 1: Đưa Code Lên GitHub

Đây là bước quan trọng nhất để lưu trữ code và kết nối với các dịch vụ deploy.

### 1. Chuẩn bị GitHub

1. Đăng ký/Đăng nhập [GitHub.com](https://github.com/).
2. Bấm vào dấu `+` ở góc trên bên phải -> chọn **New repository**.
3. Đặt tên (ví dụ: `App-Quant-Trading`).
4. Chọn **Public**.
5. Bấm **Create repository**.
6. **Copy đường dẫn HTTPS** của repo (ví dụ: `https://github.com/TênBạn/App-Quant-Trading.git`).

### 2. Cấu hình Git trên máy tính

Mở **Terminal** (hoặc CMD/PowerShell) tại thư mục dự án của bạn (`quant_trading_app`) và chạy lần lượt các lệnh sau:

```bash
# 1. Khởi tạo Git (nếu chưa làm)
git init

# 2. Thêm toàn bộ file vào danh sách theo dõi
git add .

# 3. Lưu phiên bản (Commit)
git commit -m "Phiên bản đầu tiên"

# 4. Đổi nhánh chính thành main
git branch -M main

# 5. Kết nối với GitHub (Dán link bạn vừa copy ở bước 1 vào đây)
git remote add origin https://github.com/TênBạn/App-Quant-Trading.git

# 6. Đẩy code lên GitHub
git push -u origin main
```

> **Lưu ý:** Nếu máy tính hỏi đăng nhập, hãy làm theo hướng dẫn để đăng nhập vào tài khoản GitHub của bạn.

---

## PHẦN 2: Deploy Backend (Lên Render)

Render là dịch vụ miễn phí để chạy server Python (Backend).

### 1. Tạo Web Service

1. Đăng ký/Đăng nhập [Render.com](https://render.com/).
2. Bấm nút **New +** và chọn **Web Service**.
3. Chọn **Build and deploy from a Git repository**.
4. Kết nối GitHub và chọn repo `App-Quant-Trading` bạn vừa tạo.

### 2. Cấu hình Render

Điền các thông tin sau (RẤT QUAN TRỌNG):

- **Name**: `backend-quant` (hoặc tên tùy thích)
- **Region**: Singapore (cho gần Việt Nam, hoặc để mặc định)
- **Branch**: `main`
- **Root Directory**: `backend` (⚠️ **Bắt buộc**: chỉ định folder chứa code python)
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py` (hoặc `uvicorn main:app --host 0.0.0.0 --port 10000`)
- **Plan**: Free

Bấm **Create Web Service**.

### 3. Lấy URL Backend

- Chờ vài phút để Render chạy (nó sẽ hiện logs cài đặt).
- Khi thấy chữ "Live", nhìn lên góc trên bên trái, copy đường dẫn dạng: `https://backend-quant.onrender.com`.
- **Lưu link này lại** để dùng cho Phần 3.

---

## PHẦN 3: Deploy Frontend (Lên Vercel)

Vercel là dịch vụ miễn phí tốt nhất cho Web React/Vite (Frontend).

1. Đăng ký/Đăng nhập [Vercel.com](https://vercel.com/).
2. Bấm **Add New...** -> **Project**.
3. Ở mục **Import Git Repository**, chọn repo `App-Quant-Trading` của bạn.

### Cấu hình Vercel

Trong màn hình "Configure Project":

1. **Framework Preset**: Chọn **Vite**.
2. **Root Directory**:
   - Bấm **Edit**.
   - Chọn thư mục `frontend`.
3. **Environment Variables** (Biến môi trường):
   - Mở rộng mục này.
   - Nhập tên (Key): `VITE_API_URL`
   - Nhập giá trị (Value): Dán link Backend của Render vào (VD: `https://backend-quant.onrender.com`).
   - Bấm **Add**.
4. Bấm **Deploy**.

---

## PHẦN 4: Kết Nối Cuối Cùng (CORS)

Sau khi Vercel chạy xong, bạn sẽ có link trang web (ví dụ: `https://app-quant-trading.vercel.app`). Tuy nhiên, Backend của bạn có thể sẽ chặn trang web này vì lý do bảo mật. Bạn cần cập nhật lại Backend.

1. Mở file `backend/main.py` trên máy tính của bạn.
2. Tìm danh sách `origins = [...]`.
3. Thêm link Vercel của bạn vào đó:

```python
origins = [
    "http://localhost:5173",
    "https://app-quant-trading.vercel.app", # <-- THÊM LINK VERCEL CỦA BẠN VÀO ĐÂY (bỏ dấu / ở cuối)
]
```

4. Lưu file và chạy lệnh cập nhật GitHub:

```bash
git add .
git commit -m "Update CORS domain"
git push
```

Render sẽ tự động phát hiện thay đổi và cập nhật Backend sau 1-2 phút.

---

## 🔁 Quy trình Cập nhật Code sau này

Mỗi khi bạn sửa code trên máy tính, chỉ cần chạy 3 lệnh sau thì cả Render và Vercel sẽ **tự động cập nhật**:

```bash
git add .
git commit -m "Mô tả bạn vừa sửa cái gì"
git push
```

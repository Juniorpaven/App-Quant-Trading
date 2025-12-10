# Quy Trình Xây Dựng Web App Giao Dịch Định Lượng (Quant Trading Web App)

**Ngày:** 2025-12-10
**Phiên bản:** v01

## Phần 1: Phân Rã Yêu Cầu và Xác định Vai trò (Decomposition)

| Chức năng Định lượng (FE) | Backend (BE) & Data Pipeline | Frontend (FE) & Giao diện |
| :--- | :--- | :--- |
| **1. Network Trend-Following (NTF):** Xây dựng đồ thị động, tính toán Spillover Momentum. | **Data Source:** Cung cấp dữ liệu giá/return đa tài sản (chứng khoán, futures) theo thời gian thực (real-time/near real-time). | **1. Network Visualization:** Hiển thị Network Graph tương tác (VD: D3.js/Cytoscape). |
| **2. Online Portfolio Selection (OPS):** Tính toán tỷ trọng (weights) theo các thuật toán (EG, ONS, CORN). | **Core Engine:** Module tính toán thuật toán hiệu suất cao (Python/C++). | **2. OPS Dashboard:** Biểu đồ Equity Curve, Regret, Portfolio Weights. |
| **3. Execution:** Giả lập/Thực thi lệnh giao dịch dựa trên tỷ trọng mới. | **API Gateway:** Kết nối với Broker/Exchange (Interactive Brokers, Binance, v.v.). | **3. Config Panel:** Thiết lập tham số (Learning Rate, TC, Lookback Window). |

-----

## Phần 2: Kiến Trúc Hệ Thống (System Architecture)

Sử dụng kiến trúc Microservices để đảm bảo tính module hóa và khả năng mở rộng.

### 2.1. Lớp Dữ Liệu (Data Layer)

| Thành phần | Công nghệ/Mô tả | Vai trò |
| :--- | :--- | :--- |
| **Dịch vụ Giá (Price Service)** | **Database:** Time-Series DB (InfluxDB hoặc TimescaleDB) để lưu trữ dữ liệu nến (OHLCV) lịch sử và tick data. | Nguồn dữ liệu thời gian thực (Historical & Live Feed). |
| **Dịch vụ Cơ bản (Fundamental Service)** | **Database:** PostgreSQL/MongoDB. | Lưu trữ thông tin tài sản, phân loại ngành (Sector/Group), dữ liệu cơ bản. |
| **Dịch vụ Network (Graph DB)** | **Neo4j** hoặc tương đương. | Lưu trữ cấu trúc mạng lưới tài sản (nodes/edges) và các chỉ số Network (VD: Centrality). **Quan trọng cho NTF.** |

### 2.2. Lớp Backend (Core Engine)

Sử dụng Python (với thư viện Pandas, NumPy, Scikit-learn) và một framework API như FastAPI/Flask.

| Microservice | Chức năng (Granular) | Công nghệ chính |
| :--- | :--- | :--- |
| **1. NTF Engine** | **1. Tính Ma trận Tương quan:** Tính toán Ma trận Tương quan Động (DCC-GARCH) hoặc Causality/MI. **2. Xây dựng Đồ thị:** Áp dụng kỹ thuật lọc (VD: Thresholding, MST) để tạo đồ thị. **3. Spillover Momentum:** Tính toán Momentum Aggregate có trọng số từ Neighbors. | Python, NetworkX/iGraph, NumPy. |
| **2. OPS Engine** | **1. Tối ưu hóa Trọng số:** Chạy các thuật toán Online Learning (EG, ONS, CORN) hàng ngày/theo chu kỳ. **2. Điều chỉnh Ràng buộc:** Áp dụng Group Sparsity Regularization theo Sector. | Python, SciPy, Custom OPS Libraries (VD: `pyalgotrade` hoặc tự xây dựng). |
| **3. Risk & Backtesting Service** | Tính toán Drawdown, Volatility, Sharpe Ratio. Giả lập hiệu suất theo lịch sử. | Python, Zipline/VectorBT (Backtesting). |
| **4. Execution/Order Service** | Xử lý lệnh giao dịch: Kiểm tra Margin/Balance, gửi lệnh qua API Broker, quản lý trạng thái lệnh (filled, partial, cancelled). | **FastAPI**, kết nối REST/WebSocket với Broker API. |

### 2.3. Lớp Frontend (Presentation Layer)

Sử dụng React/Vue.js.

| Component | Chức năng (Granular) | Thư viện/Công nghệ |
| :--- | :--- | :--- |
| **1. Network Graph Visualizer** | Hiển thị Network Graph. Cho phép người dùng chọn tài sản/sector để làm nổi bật liên kết. Hiển thị Spillover Score (tín hiệu). | **D3.js** hoặc **Cytoscape.js**. |
| **2. OPS Allocation Dashboard** | Biểu đồ tròn/thanh hiển thị tỷ trọng hiện tại. Biểu đồ Heatmap hiển thị sự thay đổi tỷ trọng theo thời gian. Bảng chi tiết **Regret** và **Turnover**. | React/Vue, **Chart.js/Plotly**. |
| **3. Strategy Config Panel** | Giao diện thân thiện để nhập các tham số: Lookback window (cho TF), Learning Rate $\eta$ (cho OPS), Trade Cost $\lambda$, Group Sparsity $\alpha$. | React Forms, State Management (Redux/Vuex). |

-----

## Phần 3: Mã Giả cho Core Logic (Python Pseudocode)

### A. NTF Engine: Tính Spillover Momentum

```python
# FILE: [2025-12-10]_TOOL_TECH_NTF Engine_v01.py (New Version)

def calculate_dynamic_network_momentum(assets_returns, lookback_window):
    """
    1. Tính ma trận tương quan động (DCC-GARCH/Rolling Correlation).
    2. Xây dựng đồ thị bằng cách lọc (VD: MST).
    3. Tính Momentum Spillover.
    """
    
    # B1: Tính Momentum Cá nhân (Signal S_i)
    momentum_df = assets_returns.rolling(window=lookback_window).mean()
    
    # B2: Tính Tương quan và Lọc (Xây dựng Network)
    correlation_matrix = assets_returns.corr()
    
    # Áp dụng Lọc (Ví dụ: Minimum Spanning Tree - để có Network G)
    G = build_filtered_network(correlation_matrix)
    
    # B3: Tính Momentum Spillover
    spillover_momentum = {}
    
    for asset in assets_returns.columns:
        # Láng giềng của tài sản i trong Network G
        neighbors = G.get_neighbors(asset) 
        
        if neighbors:
            # Trọng số có thể là inverse distance/correlation strength
            weights = calculate_weights(asset, neighbors, correlation_matrix) 
            
            # Momentum i (tín hiệu chính) + Momentum từ Láng giềng (Spillover)
            weighted_neighbor_momentum = sum(weights[j] * momentum_df.iloc[-1][j] for j in neighbors)
            
            # Tín hiệu cuối cùng: Kết hợp giữa Momentum riêng và Spillover
            final_signal = 0.5 * momentum_df.iloc[-1][asset] + 0.5 * weighted_neighbor_momentum
            spillover_momentum[asset] = final_signal
        else:
            spillover_momentum[asset] = momentum_df.iloc[-1][asset]
            
    return spillover_momentum

# Ghi chú: Hàm build_filtered_network và calculate_weights cần được triển khai riêng.
```

### B. OPS Engine: Thuật toán Tối ưu hóa (Ví dụ: EG - Exponential Gradient)

```python
# FILE: [2025-12-10]_TOOL_TECH_OPS Engine_v01.py (New Version)

def exponential_gradient_update(current_weights, asset_returns_t, learning_rate):
    """
    Cập nhật tỷ trọng danh mục (weights) theo thuật toán Exponential Gradient.
    Mục tiêu: Đảm bảo tỷ trọng mới giảm Regret so với kỳ trước.
    """
    # 1. Tính toán Lợi nhuận Danh mục hiện tại
    portfolio_return = np.dot(current_weights, asset_returns_t) # R_p,t
    
    # 2. Tính toán Lợi nhuận tương đối (được chuẩn hóa)
    # Lợi nhuận của tài sản so với lợi nhuận danh mục
    relative_returns = asset_returns_t / portfolio_return 
    
    # 3. Cập nhật Tỷ trọng (Update Rule) - Thêm Regularization nếu cần
    # w_i,t+1 ~ w_i,t * exp(eta * relative_returns_i)
    numerator = current_weights * np.exp(learning_rate * relative_returns)
    
    # 4. Chuẩn hóa (Normalization)
    new_weights = numerator / np.sum(numerator)
    
    # CÓ THỂ THÊM: Áp dụng Group Sparsity Regularization ở đây trước khi trả về
    # new_weights = apply_group_sparsity(new_weights, sectors, alpha)
    
    return new_weights
```

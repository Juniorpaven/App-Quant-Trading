import numpy as np

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
    
    # Map tên assets sang index của Graph
    asset_names = assets_returns.columns.tolist()
    
    for asset in asset_names:
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


def build_filtered_network(correlation_matrix):
    """
    Xây dựng Mạng lưới Lọc thông tin (Filtered Network) sử dụng Cây khung nhỏ nhất (MST).
    Khoảng cách được tính dựa trên hệ số tương quan: d(i, j) = sqrt(2 * (1 - rho(i, j)))
    Sử dụng thuật toán Prim để không phụ thuộc vào thư viện ngoài (networkx).
    """
    assets = correlation_matrix.columns.tolist()
    n = len(assets)
    
    # Tạo ma trận khoảng cách
    # rho thuộc [-1, 1], distance thuộc [0, 2]
    # np.sqrt có thể sinh warning nếu có lỗi số học nhỏ làm < 0, nên clip
    corr_values = correlation_matrix.values
    dists = np.sqrt(np.clip(2 * (1 - corr_values), 0, None))
    
    # Thuật toán Prim
    selected = [False] * n
    min_edge = [float('inf')] * n
    parent = [-1] * n
    
    min_edge[0] = 0
    
    adjacency = {asset: [] for asset in assets}
    
    for _ in range(n):
        # Tìm đỉnh chưa chọn có min_edge nhỏ nhất
        u = -1
        min_val = float('inf')
        for i in range(n):
            if not selected[i] and min_edge[i] < min_val:
                min_val = min_edge[i]
                u = i
        
        if u == -1: break
        
        selected[u] = True
        
        # Nếu có parent, thêm cạnh vào đồ thị
        if parent[u] != -1:
            u_name = assets[u]
            p_name = assets[parent[u]]
            adjacency[u_name].append(p_name)
            adjacency[p_name].append(u_name)
            
        # Cập nhật neighbors
        for v in range(n):
            if not selected[v] and dists[u][v] < min_edge[v]:
                min_edge[v] = dists[u][v]
                parent[v] = u
                
    return NetworkWrapper(adjacency)

class NetworkWrapper:
    def __init__(self, adjacency_map):
        self.adjacency_map = adjacency_map
        
    def get_neighbors(self, asset):
        return self.adjacency_map.get(asset, [])

def calculate_weights(asset, neighbors, correlation_matrix):
    """
    Tính trọng số ảnh hưởng từ các láng giềng dựa trên độ mạnh tương quan (trị tuyệt đối).
    """
    weights = {}
    total_corr = 0
    
    for neighbor in neighbors:
        # Lấy trị tuyệt đối của tương quan làm trọng số
        corr = abs(correlation_matrix.loc[asset, neighbor])
        weights[neighbor] = corr
        total_corr += corr
        
    # Chuẩn hóa trọng số sao cho tổng bằng 1 
    if total_corr > 0:
        for neighbor in weights:
            weights[neighbor] /= total_corr
            
    return weights


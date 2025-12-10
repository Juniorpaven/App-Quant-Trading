
import numpy as np

def exponential_gradient_update(current_weights, asset_returns_t, learning_rate, group_mapping=None, alpha=0.0):
    """
    Cập nhật tỷ trọng danh mục (weights) theo thuật toán Exponential Gradient.
    Mục tiêu: Đảm bảo tỷ trọng mới giảm Regret so với kỳ trước.
    Optional: Áp dụng Group Sparsity Regularization nếu có group_mapping và alpha > 0.
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
    
    # 5. Áp dụng Regularization (Group Sparsity) nếu được yêu cầu
    if group_mapping is not None and alpha > 0:
        new_weights = apply_group_sparsity(new_weights, group_mapping, alpha)
        
    return new_weights

def apply_group_sparsity(weights, group_mapping, alpha):
    """
    Áp dụng Regularization thưa theo nhóm (Group Sparsity).
    Mục tiêu: Loại bỏ các nhóm (ngành) có tỷ trọng nhỏ, tập trung vốn vào các nhóm hiệu quả.
    
    Args:
        weights (np.array): Mảng tỷ trọng tài sản hiện tại.
        group_mapping (dict): Map index của tài sản tới index của nhóm/ngành. 
                              VD: {0: 'Tech', 1: 'Tech', 2: 'Finance', ...}
                              Hoặc index nhóm: {0: 0, 1: 0, 2: 1, ...}
        alpha (float): Hệ số Regularization (ngưỡng cắt).
    
    Returns:
        np.array: Tỷ trọng mới đã qua regularize và chuẩn hóa lại.
    """
    # Xác định các nhóm duy nhất
    groups = np.unique(list(group_mapping.values()))
    
    # Tạo copy để không ảnh hưởng mảng gốc lúc tính toán
    regularized_weights = weights.copy()
    
    # Duyệt qua từng nhóm
    for g in groups:
        # Lấy indices của các tài sản thuộc nhóm g
        asset_indices = [i for i, group_id in group_mapping.items() if group_id == g]
        
        if not asset_indices:
            continue
            
        # Lấy vector trọng số của nhóm r_g
        w_g = weights[asset_indices]
        
        # Tính L2 Norm của nhóm ||w_g||_2
        norm_g = np.linalg.norm(w_g)
        
        # Áp dụng Soft Thresholding lên Norm
        # factor = max(0, 1 - alpha / norm_g)
        if norm_g == 0:
            factor = 0
        else:
            factor = max(0, 1 - alpha / norm_g)
            
        # Cập nhật trọng số tài sản trong nhóm
        regularized_weights[asset_indices] = w_g * factor
        
    # Chuẩn hóa lại để tổng bằng 1 (Chiếu lên Simplex)
    if np.sum(regularized_weights) > 0:
        regularized_weights /= np.sum(regularized_weights)
    else:
        # Trường hợp hiếm: tất cả bị cắt về 0 -> chia đều (fallback)
        n = len(weights)
        regularized_weights = np.ones(n) / n
        
    return regularized_weights

import numpy as np


def random_box_optimizer_3d(prod_w, prod_l, prod_h, units):
    best_dims = None
    best_score = 0
    target_volume = prod_w * prod_l * prod_h * units
    for _ in range(200):
        w_ = np.random.uniform(prod_w, prod_w * 5)
        l_ = np.random.uniform(prod_l, prod_l * 5)
        h_ = np.random.uniform(prod_h, prod_h * 5)
        vol = w_ * l_ * h_
        ratio = min(vol, target_volume) / max(vol, target_volume)
        if ratio > best_score:
            best_score = ratio
            best_dims = (w_, l_, h_)
    return best_dims, best_score

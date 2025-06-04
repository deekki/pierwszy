import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from packing_app.core.algorithms import pack_rectangles_mixed_greedy


def compute_interlocked_layout(pallet_w, pallet_l, box_w, box_l, num_layers=4):
    """Return positions for standard and interlocked stacking."""
    count, base_positions = pack_rectangles_mixed_greedy(pallet_w, pallet_l, box_w, box_l)

    # base layout repeated for each layer
    base_layers = [base_positions for _ in range(num_layers)]

    # determine possible shift (half box size) without leaving pallet bounds
    min_x = min(x for x, y, w, h in base_positions)
    max_x = max(x + w for x, y, w, h in base_positions)
    min_y = min(y for x, y, w, h in base_positions)
    max_y = max(y + h for x, y, w, h in base_positions)

    shift_x = 0.0
    shift_y = 0.0
    if min_x >= box_w / 2 and max_x + box_w / 2 <= pallet_w:
        shift_x = box_w / 2
    elif min_y >= box_l / 2 and max_y + box_l / 2 <= pallet_l:
        shift_y = box_l / 2

    interlocked_layers = []
    for layer_idx in range(num_layers):
        if layer_idx % 2 == 0:
            interlocked_layers.append(base_positions)
        else:
            shifted = [(x + shift_x, y + shift_y, w, h) for x, y, w, h in base_positions]
            interlocked_layers.append(shifted)

    return count, base_layers, interlocked_layers


def plot_layers(ax, layers, pallet_w, pallet_l, title):
    ax.add_patch(Rectangle((0, 0), pallet_w, pallet_l, fill=False, edgecolor="black", linewidth=2))
    for idx, layer in enumerate(layers):
        color = "tab:blue" if idx % 2 == 0 else "tab:orange"
        for x, y, w, h in layer:
            ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="black", alpha=0.5))
    ax.set_xlim(-50, pallet_w + 50)
    ax.set_ylim(-50, pallet_l + 50)
    ax.set_aspect("equal")
    ax.set_title(f"{title}\nCartons per layer: {len(layers[0])}")


def main():
    pallet_w = 1200
    pallet_l = 800
    box_w = 400
    box_l = 300

    count, base, interlocked = compute_interlocked_layout(pallet_w, pallet_l, box_w, box_l)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    plot_layers(axes[0], base, pallet_w, pallet_l, "Standard")
    plot_layers(axes[1], interlocked, pallet_w, pallet_l, "Interlocked")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

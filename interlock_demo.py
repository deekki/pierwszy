import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from packing_app.core.algorithms import compute_interlocked_layout


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

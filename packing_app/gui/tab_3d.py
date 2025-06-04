import tkinter as tk
from tkinter import ttk, messagebox
from packing_app.core.algorithms import random_box_optimizer_3d
from core.utils import load_cartons

class TabBox3D(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.predefined_cartons = load_cartons()
        self.build_ui()

    def build_ui(self):
        fr = ttk.Frame(self)
        fr.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(fr, text="Wymiary produktu (W, L, H) [mm]:").grid(row=0, column=0, sticky="w")
        self.prod_w = tk.DoubleVar(value=50)
        self.prod_l = tk.DoubleVar(value=50)
        self.prod_h = tk.DoubleVar(value=20)
        ttk.Entry(fr, textvariable=self.prod_w, width=8).grid(row=0, column=1, padx=5)
        ttk.Entry(fr, textvariable=self.prod_l, width=8).grid(row=0, column=2, padx=5)
        ttk.Entry(fr, textvariable=self.prod_h, width=8).grid(row=0, column=3, padx=5)

        ttk.Label(fr, text="Ilość opakowań w kartonie:").grid(row=1, column=0, sticky="w")
        self.num_units = tk.IntVar(value=20)
        ttk.Entry(fr, textvariable=self.num_units, width=8).grid(row=1, column=1, padx=5)

        self.btn_search = ttk.Button(fr, text="Znajdź najlepsze kartony", command=self.search_best_boxes)
        self.btn_search.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.btn_opt = ttk.Button(fr, text="Optymalizuj (losowo)", command=self.optimize_box_random)
        self.btn_opt.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.listbox = tk.Listbox(self, width=80, height=15)
        self.listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def search_best_boxes(self):
        self.listbox.delete(0, tk.END)
        w_ = self.prod_w.get()
        l_ = self.prod_l.get()
        h_ = self.prod_h.get()
        product_volume = w_ * l_ * h_
        results = []
        for key, dims in self.predefined_cartons.items():
            bw, bl, bh = dims
            bw_ext, bl_ext, bh_ext = bw + 3, bl + 3, bh + 6
            layers = int(bh_ext // h_)
            base_count = int(bw_ext // w_) * int(bl_ext // l_)
            total_cnt = base_count * layers
            box_vol = bw_ext * bl_ext * bh_ext
            util = (total_cnt * product_volume) / box_vol if box_vol > 0 else 0
            results.append((key, bw_ext, bl_ext, bh_ext, total_cnt, util))
        results.sort(key=lambda x: (x[5], x[4]), reverse=True)
        for r in results[:10]:
            key, bw_ext, bl_ext, bh_ext, cnt, ut = r
            msg = f"{key}: {int(bw_ext)}x{int(bl_ext)}x{int(bh_ext)} mm | szt={cnt} | użycie={ut*100:.1f}%"
            self.listbox.insert(tk.END, msg)

    def optimize_box_random(self):
        self.listbox.delete(0, tk.END)
        w_ = self.prod_w.get()
        l_ = self.prod_l.get()
        h_ = self.prod_h.get()
        units = self.num_units.get()
        best_dims, best_score = random_box_optimizer_3d(w_, l_, h_, units)
        if best_dims is None:
            messagebox.showinfo("Wynik", "Nie znaleziono rozwiązania.")
        else:
            wopt, lopt, hopt = best_dims
            msg = f"Najlepsze wymiary (losowo):\n{wopt:.1f} x {lopt:.1f} x {hopt:.1f} mm\nDopasowanie: {best_score*100:.1f}%"
            messagebox.showinfo("Optymalizacja 3D", msg)


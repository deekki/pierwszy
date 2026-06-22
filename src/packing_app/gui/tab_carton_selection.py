from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from packing_app.core.carton_selection import rank_cartons
from packing_app.data.repository import load_cartons, load_pallets_with_weights
from packing_app.gui.pallet_input_parsing import parse_dim


class TabCartonSelection(ttk.Frame):
    def __init__(self, parent, pallet_tab=None):
        super().__init__(parent)
        self.pallet_tab = pallet_tab
        self.cartons = load_cartons()
        self.pallets = load_pallets_with_weights()
        self.width_var = tk.StringVar(value="")
        self.length_var = tk.StringVar(value="")
        self.height_var = tk.StringVar(value="")
        self.diameter_var = tk.StringVar(value="")
        self.mass_var = tk.StringVar(value="")
        self.max_height_var = tk.StringVar(value="1600")
        self.include_pallet_height_var = tk.BooleanVar(value=True)
        self.clearance_var = tk.StringVar(value="0")
        self.max_mass_var = tk.StringVar(value="600")
        self._rows: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        form = ttk.LabelFrame(self, text="Dane produktu")
        form.pack(fill="x", padx=8, pady=8)
        labels = [
            ("Szerokość [mm]", self.width_var), ("Długość [mm]", self.length_var),
            ("Wysokość [mm]", self.height_var), ("lub średnica [mm]", self.diameter_var),
            ("Masa produktu [kg]", self.mass_var), ("Maks. wysokość palety [mm]", self.max_height_var),
            ("Minimalny luz [mm]", self.clearance_var), ("Maks. masa palety [kg]", self.max_mass_var),
        ]
        for i, (text, var) in enumerate(labels):
            ttk.Label(form, text=text).grid(row=i // 4, column=(i % 4) * 2, sticky="w", padx=4, pady=4)
            ttk.Entry(form, textvariable=var, width=10).grid(row=i // 4, column=(i % 4) * 2 + 1, sticky="w", padx=4, pady=4)
        ttk.Checkbutton(form, text="wysokość zawiera nośnik", variable=self.include_pallet_height_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=4)
        ttk.Button(form, text="Porównaj kartony", command=self.calculate).grid(row=2, column=2, padx=4, pady=4, sticky="w")
        ttk.Button(form, text="Przenieś do Paletyzacji", command=self.transfer_to_palletization).grid(row=2, column=3, columnspan=2, padx=4, pady=4, sticky="w")

        columns = ("carton", "pieces", "eff", "orientation", "c_layer", "layers", "c_pallet", "p_pallet", "height", "mass", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16)
        headings = {"carton":"Karton", "pieces":"Szt./karton", "eff":"Wyk. obj. [%]", "orientation":"Orientacja", "c_layer":"Kart./warstwę", "layers":"Warstwy", "c_pallet":"Kart./paletę", "p_pallet":"Prod./paletę", "height":"Wys. [mm]", "mass":"Masa [kg]", "status":"Status / ostrzeżenia"}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=120 if col in {"carton", "status", "orientation"} else 90, anchor="w" if col in {"carton", "status"} else "e")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _product_dims(self):
        diameter = parse_dim(self.diameter_var)
        w = parse_dim(self.width_var) or diameter
        l = parse_dim(self.length_var) or diameter
        h = parse_dim(self.height_var)
        if min(w, l, h) <= 0:
            raise ValueError("Podaj szerokość/długość/wysokość produktu albo średnicę oraz wysokość.")
        return (w, l, h)

    def calculate(self) -> None:
        try:
            mass = parse_dim(self.mass_var)
            results = rank_cartons(
                self.cartons, self.pallets, product_dims=self._product_dims(),
                product_mass=mass if mass > 0 else None,
                max_pallet_height=parse_dim(self.max_height_var) or 1600,
                include_pallet_height=self.include_pallet_height_var.get(),
                clearance=parse_dim(self.clearance_var),
                max_pallet_mass=parse_dim(self.max_mass_var) or 600,
            )
        except ValueError as exc:
            messagebox.showerror("Dobór kartonu", str(exc)); return
        self._rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for rec in results:
            iid = rec.carton_name
            self._rows[iid] = rec.carton_name
            self.tree.insert("", "end", iid=iid, values=(rec.carton_name, rec.pieces_per_carton, f"{rec.carton_volume_eff*100:.1f}", " × ".join(f"{v:.0f}" for v in rec.orientation), rec.cartons_per_layer, rec.layers, rec.cartons_per_pallet, rec.products_per_pallet, f"{rec.pallet_height:.1f}", "" if rec.pallet_mass is None else f"{rec.pallet_mass:.2f}", rec.status))

    def transfer_to_palletization(self) -> None:
        selected = self.tree.selection()
        if not selected or self.pallet_tab is None:
            messagebox.showinfo("Dobór kartonu", "Wybierz karton z tabeli."); return
        self.pallet_tab.apply_carton_selection(selected[0], max_stack=parse_dim(self.max_height_var) or 1600, include_pallet_height=self.include_pallet_height_var.get())

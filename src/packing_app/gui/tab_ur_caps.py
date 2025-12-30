import json
import logging
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from palletizer_core.pally_export import (
    PallyExportConfig,
    build_pally_json,
    find_out_of_bounds,
)
from packing_app.core.pallet_snapshot import PalletSnapshot

logger = logging.getLogger(__name__)


class TabURCaps(ttk.Frame):
    def __init__(self, parent, pallet_tab):
        super().__init__(parent)
        self.pallet_tab = pallet_tab
        self.active_snapshot: PalletSnapshot | None = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.pally_name_var = tk.StringVar(value="export")
        self.pally_out_dir_var = tk.StringVar(value=os.path.join(base_dir, "pally_exports"))
        self.pally_slip_vars: list[tk.BooleanVar] = []
        self.pally_label_orientation_map = {
            "Przód": 0,
            "Lewy bok": -90,
            "Prawy bok": 90,
            "Tył": 180,
        }
        self.pally_label_orientation_display_var = tk.StringVar(value="Tył")
        self.pally_swap_axes_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="")
        self.snapshot_summary_var = tk.StringVar(value="Brak danych z Paletyzacji")
        self.weight_summary_var = tk.StringVar(value="Masa kartonu: -")

        self.build_ui()

    def build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.columnconfigure(0, weight=1)

        fetch_frame = ttk.Frame(main_frame)
        fetch_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        fetch_frame.columnconfigure(1, weight=1)

        ttk.Button(
            fetch_frame,
            text="Pobierz z Paletyzacji",
            command=self.fetch_from_pallet,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        ttk.Label(fetch_frame, textvariable=self.snapshot_summary_var, justify="left").grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(fetch_frame, textvariable=self.weight_summary_var, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        export_frame = ttk.LabelFrame(main_frame, text="Eksport UR CAPS")
        export_frame.grid(row=1, column=0, sticky="nsew")
        export_frame.columnconfigure(1, weight=1)

        ttk.Label(export_frame, text="Nazwa:").grid(row=0, column=0, padx=4, pady=4, sticky="e")
        ttk.Entry(export_frame, textvariable=self.pally_name_var, width=28).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )

        ttk.Label(export_frame, text="Folder:").grid(row=1, column=0, padx=4, pady=4, sticky="e")
        folder_frame = ttk.Frame(export_frame)
        folder_frame.grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(folder_frame, textvariable=self.pally_out_dir_var).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        ttk.Button(folder_frame, text="...", width=3, command=self._choose_directory).grid(
            row=0, column=1
        )

        ttk.Label(export_frame, text="Kierunek etykiety:").grid(
            row=2, column=0, padx=4, pady=4, sticky="e"
        )
        ttk.Combobox(
            export_frame,
            textvariable=self.pally_label_orientation_display_var,
            values=list(self.pally_label_orientation_map.keys()),
            state="readonly",
            width=25,
        ).grid(row=2, column=1, padx=4, pady=4, sticky="w")

        ttk.Checkbutton(
            export_frame,
            text="Swap axes for PALLY (EUR)",
            variable=self.pally_swap_axes_var,
        ).grid(row=3, column=0, columnspan=2, padx=4, pady=4, sticky="w")

        ttk.Label(export_frame, text="Przekładka po warstwie:").grid(
            row=4, column=0, padx=4, pady=4, sticky="ne"
        )
        self.pally_slip_frame = ttk.Frame(export_frame)
        self.pally_slip_frame.grid(row=4, column=1, padx=4, pady=4, sticky="w")

        ttk.Button(
            export_frame,
            text="Eksportuj PALLY JSON",
            command=self.export_pally_json,
        ).grid(row=5, column=0, columnspan=2, padx=4, pady=(8, 4), sticky="ew")

        ttk.Label(export_frame, textvariable=self.status_var, justify="left").grid(
            row=6, column=0, columnspan=2, padx=4, pady=(2, 0), sticky="w"
        )

    def fetch_from_pallet(self, quiet_if_missing: bool = False) -> None:
        snapshot = getattr(self.pallet_tab, "last_snapshot", None)
        if snapshot is None:
            message = "Brak zapisanego układu w zakładce Paletyzacja."
            if quiet_if_missing:
                self.status_var.set(message)
                return
            messagebox.showinfo("UR CAPS", message)
            return
        self.apply_snapshot(snapshot)

    def apply_snapshot(self, snapshot: PalletSnapshot) -> None:
        self.active_snapshot = snapshot
        self._update_snapshot_summary(snapshot)
        self._update_slip_checkboxes(snapshot.num_layers or len(snapshot.layers))
        for idx, var in enumerate(self.pally_slip_vars):
            if idx and idx in snapshot.slips_after:
                var.set(True)
        self.pally_swap_axes_var.set(snapshot.pallet_w > snapshot.pallet_l)
        self.status_var.set("Pobrano dane z Paletyzacji")
        self._update_weight_summary()

    def _update_snapshot_summary(self, snapshot: PalletSnapshot) -> None:
        pallet = f"Paleta: {snapshot.pallet_w} × {snapshot.pallet_l} × {snapshot.pallet_h} mm"
        box = f"Karton: {snapshot.box_w} × {snapshot.box_l} × {snapshot.box_h} mm"
        layers = f"Warstwy: {len(snapshot.layers)}"
        self.snapshot_summary_var.set(f"{pallet} | {box} | {layers}")

    def _update_weight_summary(self) -> None:
        weight_g, source = self._get_box_weight_g()
        if weight_g:
            source_label = "ręcznie" if source == "manual" else "katalog"
            self.weight_summary_var.set(
                f"Masa kartonu: {weight_g / 1000:.3f} kg ({source_label})"
            )
        else:
            self.weight_summary_var.set("Masa kartonu: brak danych")

    def _update_slip_checkboxes(self, layer_count: int) -> None:
        for widget in self.pally_slip_frame.winfo_children():
            widget.destroy()
        self.pally_slip_vars.clear()
        base_var = tk.BooleanVar(value=True)
        self.pally_slip_vars.append(base_var)
        ttk.Checkbutton(
            self.pally_slip_frame,
            text="0",
            variable=base_var,
            state="disabled",
        ).grid(row=0, column=0, padx=2, pady=0, sticky="w")

        for idx in range(1, layer_count + 1):
            var = tk.BooleanVar(value=False)
            self.pally_slip_vars.append(var)
            ttk.Checkbutton(
                self.pally_slip_frame,
                text=str(idx),
                variable=var,
            ).grid(row=0, column=idx, padx=2, pady=0, sticky="w")

    def _selected_slip_layers(self) -> set[int]:
        slips: set[int] = set()
        for idx, var in enumerate(self.pally_slip_vars):
            if idx == 0:
                continue
            if var.get():
                slips.add(idx)
        return slips

    @staticmethod
    def _slugify_filename(value: str) -> str:
        slug = re.sub(r"[^\w\-]+", "_", value.strip().lower())
        slug = slug.strip("_")
        return slug or "export"

    def _choose_directory(self) -> None:
        path = filedialog.askdirectory(initialdir=self.pally_out_dir_var.get())
        if path:
            self.pally_out_dir_var.set(path)

    def _get_box_weight_g(self) -> tuple[int, str]:
        if hasattr(self.pallet_tab, "_get_active_carton_weight"):
            weight_kg, source = self.pallet_tab._get_active_carton_weight()  # pylint: disable=protected-access
            return int(round(max(weight_kg, 0.0) * 1000)), source
        return 0, "unknown"

    def export_pally_json(self) -> None:
        snapshot = self.active_snapshot
        if snapshot is None:
            messagebox.showwarning("UR CAPS", "Brak danych do eksportu.")
            return
        if not snapshot.layers:
            messagebox.showwarning("UR CAPS", "Brak warstw do eksportu.")
            return

        name = self.pally_name_var.get().strip() or "export"
        out_dir = self.pally_out_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("Brak folderu", "Podaj folder zapisu.")
            return

        pallet_w = int(round(snapshot.pallet_w))
        pallet_l = int(round(snapshot.pallet_l))
        pallet_h = int(round(snapshot.pallet_h))

        box_w = int(round(snapshot.box_w + 2 * snapshot.thickness))
        box_l = int(round(snapshot.box_l + 2 * snapshot.thickness))
        box_h = int(round(snapshot.box_h + 2 * snapshot.thickness))

        box_weight_g, _ = self._get_box_weight_g()
        if not box_weight_g:
            messagebox.showwarning(
                "Brak masy",
                "Brak masy kartonu. Uzupełnij pole w zakładce Paletyzacja.",
            )
            return

        layer_rects_list = snapshot.layer_rects_list
        if not layer_rects_list:
            messagebox.showwarning("UR CAPS", "Brak współrzędnych warstw w snapshot.")
            return

        config = PallyExportConfig(
            name=name,
            pallet_w=pallet_w,
            pallet_l=pallet_l,
            pallet_h=pallet_h,
            box_w=box_w,
            box_l=box_l,
            box_h=box_h,
            box_weight_g=box_weight_g,
            overhang_ends=0,
            overhang_sides=0,
            label_orientation=self.pally_label_orientation_map.get(
                self.pally_label_orientation_display_var.get(), 180
            ),
            swap_axes_for_pally=bool(self.pally_swap_axes_var.get()),
        )

        payload = build_pally_json(
            config=config,
            layer_rects_list=layer_rects_list,
            slips_after=self._selected_slip_layers(),
        )

        warnings = find_out_of_bounds(payload)
        if warnings:
            self.status_var.set(f"Błąd: {warnings[0]}")
            return

        os.makedirs(out_dir, exist_ok=True)
        filename = f"{self._slugify_filename(name)}.json"
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
        self.status_var.set(f"Zapisano PALLY JSON: {path}")


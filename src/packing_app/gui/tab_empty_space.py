from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from packing_app.core.empty_space import (
    EmptySpaceResult,
    calculate_empty_space,
    volume_oblong_mm3,
    volume_oval_mm3,
    volume_round_mm3,
)


class TabEmptySpaceContainers(ttk.Frame):
    """Zakładka do obliczania pustej przestrzeni w pojemniku typu pilljar."""

    SHAPE_ROUND = "okrągły"
    SHAPE_OVAL = "owalny"
    SHAPE_OBLONG = "podłużny"

    def __init__(self, parent):
        super().__init__(parent)
        self.shape_var = tk.StringVar(value=self.SHAPE_ROUND)
        self.quantity_var = tk.StringVar(value="1")
        self.container_volume_var = tk.StringVar(value="50")

        self.diameter_var = tk.StringVar(value="")
        self.length_var = tk.StringVar(value="")
        self.width_var = tk.StringVar(value="")
        self.height_var = tk.StringVar(value="")
        self.total_length_var = tk.StringVar(value="")

        self.warning_var = tk.StringVar(value="")
        self.result_unit_mm3_var = tk.StringVar(value="-")
        self.result_unit_cc_var = tk.StringVar(value="-")
        self.result_total_cc_var = tk.StringVar(value="-")
        self.result_fill_percent_var = tk.StringVar(value="-")
        self.result_empty_percent_var = tk.StringVar(value="-")
        self.result_free_cc_var = tk.StringVar(value="-")

        self._numeric_vcmd = (self.register(self._validate_decimal_input), "%P")
        self._integer_vcmd = (self.register(self._validate_integer_input), "%P")

        self._dimensions_frame: ttk.Frame | None = None
        self.build_ui()

    def build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        form = ttk.LabelFrame(self, text="Parametry")
        form.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Kształt:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        shape_combo = ttk.Combobox(
            form,
            textvariable=self.shape_var,
            values=[self.SHAPE_ROUND, self.SHAPE_OVAL, self.SHAPE_OBLONG],
            state="readonly",
            width=20,
        )
        shape_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        shape_combo.bind("<<ComboboxSelected>>", self._on_shape_changed)

        ttk.Label(form, text="Liczba sztuk:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(
            form,
            textvariable=self.quantity_var,
            width=20,
            validate="key",
            validatecommand=self._integer_vcmd,
        ).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(form, text="Objętość pojemnika [cc]:").grid(
            row=2, column=0, sticky="e", padx=4, pady=4
        )
        ttk.Entry(
            form,
            textvariable=self.container_volume_var,
            width=20,
            validate="key",
            validatecommand=self._numeric_vcmd,
        ).grid(row=2, column=1, sticky="w", padx=4, pady=4)

        self._dimensions_frame = ttk.LabelFrame(self, text="Wymiary jednostki")
        self._dimensions_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        self._dimensions_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, sticky="w", padx=8, pady=(4, 8))
        ttk.Button(button_frame, text="Oblicz", command=self.calculate).pack(side=tk.LEFT)

        results = ttk.LabelFrame(self, text="Wyniki")
        results.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

        self._result_row(results, 0, "Objętość 1 sztuki [mm³]:", self.result_unit_mm3_var)
        self._result_row(results, 1, "Objętość 1 sztuki [cc]:", self.result_unit_cc_var)
        self._result_row(results, 2, "Objętość całkowita [cc]:", self.result_total_cc_var)
        self._result_row(results, 3, "Zajętość pojemnika [%]:", self.result_fill_percent_var)
        self._result_row(results, 4, "Pusta przestrzeń [%]:", self.result_empty_percent_var)
        self._result_row(results, 5, "Wolna objętość [cc]:", self.result_free_cc_var)

        ttk.Label(self, textvariable=self.warning_var, foreground="#b44d00").grid(
            row=4, column=0, sticky="w", padx=10, pady=(0, 8)
        )

        self._render_dimension_fields()

    def _result_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=2)
        ttk.Label(parent, textvariable=variable).grid(row=row, column=1, sticky="e", padx=6, pady=2)

    def _render_dimension_fields(self) -> None:
        if self._dimensions_frame is None:
            return
        for widget in self._dimensions_frame.winfo_children():
            widget.destroy()

        shape = self.shape_var.get()
        if shape == self.SHAPE_ROUND:
            self._add_dimension_entry(0, "Średnica [mm]:", self.diameter_var)
        elif shape == self.SHAPE_OVAL:
            self._add_dimension_entry(0, "Długość [mm]:", self.length_var)
            self._add_dimension_entry(1, "Szerokość [mm]:", self.width_var)
            self._add_dimension_entry(2, "Wysokość / grubość [mm]:", self.height_var)
        elif shape == self.SHAPE_OBLONG:
            self._add_dimension_entry(0, "Długość [mm]:", self.total_length_var)
            self._add_dimension_entry(1, "Średnica [mm]:", self.diameter_var)

    def _add_dimension_entry(self, row: int, label: str, variable: tk.StringVar) -> None:
        assert self._dimensions_frame is not None
        ttk.Label(self._dimensions_frame, text=label).grid(row=row, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(
            self._dimensions_frame,
            textvariable=variable,
            width=20,
            validate="key",
            validatecommand=self._numeric_vcmd,
        ).grid(row=row, column=1, sticky="w", padx=4, pady=4)

    def _on_shape_changed(self, _: tk.Event) -> None:
        self.warning_var.set("")
        self._clear_results()
        self._render_dimension_fields()

    def calculate(self) -> None:
        try:
            quantity = self._parse_positive_integer(self.quantity_var.get(), "Liczba sztuk")
            container_cc = self._parse_positive_float(
                self.container_volume_var.get(), "Objętość pojemnika [cc]"
            )
            unit_volume_mm3 = self._calculate_unit_volume_mm3()
            result = calculate_empty_space(
                unit_volume_mm3=unit_volume_mm3,
                quantity=quantity,
                container_volume_cc=container_cc,
            )
        except ValueError as error:
            self.warning_var.set(str(error))
            self._clear_results()
            return

        self._show_results(result)

    def _calculate_unit_volume_mm3(self) -> float:
        shape = self.shape_var.get()
        if shape == self.SHAPE_ROUND:
            diameter_mm = self._parse_positive_float(self.diameter_var.get(), "Średnica [mm]")
            return volume_round_mm3(diameter_mm)
        if shape == self.SHAPE_OVAL:
            length_mm = self._parse_positive_float(self.length_var.get(), "Długość [mm]")
            width_mm = self._parse_positive_float(self.width_var.get(), "Szerokość [mm]")
            height_mm = self._parse_positive_float(self.height_var.get(), "Wysokość / grubość [mm]")
            return volume_oval_mm3(length_mm, width_mm, height_mm)

        total_length_mm = self._parse_positive_float(self.total_length_var.get(), "Długość [mm]")
        diameter_mm = self._parse_positive_float(self.diameter_var.get(), "Średnica [mm]")
        return volume_oblong_mm3(total_length_mm, diameter_mm)

    def _show_results(self, result: EmptySpaceResult) -> None:
        self.result_unit_mm3_var.set(self._format_number(result.volume_unit_mm3, 3))
        self.result_unit_cc_var.set(self._format_number(result.volume_unit_cc, 6))
        self.result_total_cc_var.set(self._format_number(result.total_volume_cc, 6))
        self.result_fill_percent_var.set(self._format_number(result.fill_percent, 2))
        self.result_empty_percent_var.set(self._format_number(result.empty_percent, 2))
        self.result_free_cc_var.set(self._format_number(result.free_volume_cc, 6))

        if result.total_volume_cc > self._parse_decimal_or_zero(self.container_volume_var.get()):
            self.warning_var.set(
                "Ostrzeżenie: objętość produktu przekracza objętość pojemnika."
            )
        else:
            self.warning_var.set("")

    def _clear_results(self) -> None:
        for variable in (
            self.result_unit_mm3_var,
            self.result_unit_cc_var,
            self.result_total_cc_var,
            self.result_fill_percent_var,
            self.result_empty_percent_var,
            self.result_free_cc_var,
        ):
            variable.set("-")

    def _parse_positive_float(self, value: str, field_name: str) -> float:
        normalized = value.replace(",", ".").strip()
        if not normalized:
            raise ValueError(f"Pole „{field_name}” jest wymagane.")
        try:
            parsed = float(normalized)
        except ValueError as error:
            raise ValueError(f"Pole „{field_name}” musi być liczbą dodatnią.") from error

        if parsed <= 0:
            raise ValueError(f"Pole „{field_name}” musi być większe od zera.")
        return parsed

    def _parse_positive_integer(self, value: str, field_name: str) -> int:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"Pole „{field_name}” jest wymagane.")
        try:
            parsed = int(normalized)
        except ValueError as error:
            raise ValueError(f"Pole „{field_name}” musi być liczbą całkowitą dodatnią.") from error

        if parsed <= 0:
            raise ValueError(f"Pole „{field_name}” musi być większe od zera.")
        return parsed

    def _parse_decimal_or_zero(self, value: str) -> float:
        try:
            return float(value.replace(",", ".").strip())
        except ValueError:
            return 0.0

    def _format_number(self, value: float, precision: int) -> str:
        return f"{value:.{precision}f}".replace(".", ",")

    def _validate_decimal_input(self, value: str) -> bool:
        if value == "":
            return True
        normalized = value.replace(",", ".")
        if normalized.count(".") > 1:
            return False
        if normalized in {".", ","}:
            return True
        try:
            return float(normalized) >= 0
        except ValueError:
            return False

    def _validate_integer_input(self, value: str) -> bool:
        if value == "":
            return True
        return value.isdigit()

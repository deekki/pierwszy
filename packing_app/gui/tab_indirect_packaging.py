import tkinter as tk
from tkinter import ttk

from .base_editor import BaseListEditor

from packing_app.data.repository import load_indirect_packaging, save_indirect_packaging


class TabIndirectPackaging(BaseListEditor):
    """Editor for indirect packaging materials."""

    def load_data(self):
        return load_indirect_packaging()

    def save_data(self):
        save_indirect_packaging(self.data_list)

    def build_ui(self):
        list_frame = ttk.Frame(self)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.listbox = tk.Listbox(list_frame, height=15)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        form = ttk.Frame(self)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        ttk.Label(form, text="Nazwa:").grid(row=0, column=0, sticky="e", pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=25).grid(row=0, column=1, pady=2)

        ttk.Label(form, text="Ilość/Jednostka:").grid(row=1, column=0, sticky="e", pady=2)
        self.qty_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.qty_var, width=25).grid(row=1, column=1, pady=2)

        ttk.Label(form, text="Komentarz:").grid(row=2, column=0, sticky="e", pady=2)
        self.comment_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.comment_var, width=25).grid(row=2, column=1, pady=2)

        ttk.Label(form, text="Waga:").grid(row=3, column=0, sticky="e", pady=2)
        self.weight_var = tk.StringVar()
        ttk.Entry(
            form,
            textvariable=self.weight_var,
            width=25,
            validate="key",
            validatecommand=(self.register(self.validate_number), "%P"),
        ).grid(row=3, column=1, pady=2)

        ttk.Label(form, text="Typ:").grid(row=4, column=0, sticky="e", pady=2)
        self.type_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.type_var, width=25).grid(row=4, column=1, pady=2)

        ttk.Label(form, text="Dostawca:").grid(row=5, column=0, sticky="e", pady=2)
        self.supplier_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.supplier_var, width=25).grid(row=5, column=1, pady=2)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Dodaj / Aktualizuj", command=self.add_update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Usuń", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Zapisz", command=self.save).pack(side=tk.LEFT, padx=2)

    def listbox_label(self, item: dict) -> str:
        return item.get("name", "")

    def clear_fields(self) -> None:
        self.name_var.set("")
        self.qty_var.set("")
        self.comment_var.set("")
        self.weight_var.set("")
        self.type_var.set("")
        self.supplier_var.set("")

    def populate_fields(self, item: dict) -> None:
        self.name_var.set(item.get("name", ""))
        self.qty_var.set(item.get("quantity", ""))
        self.comment_var.set(item.get("comment", ""))
        self.weight_var.set(item.get("weight", ""))
        self.type_var.set(item.get("type", ""))
        self.supplier_var.set(item.get("supplier", ""))

    def collect_data(self) -> dict:
        return {
            "name": self.name_var.get(),
            "quantity": self.qty_var.get(),
            "comment": self.comment_var.get(),
            "weight": self.weight_var.get(),
            "type": self.type_var.get(),
            "supplier": self.supplier_var.get(),
        }


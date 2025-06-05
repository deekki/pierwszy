import tkinter as tk
from tkinter import ttk, messagebox

from core.utils import load_cartons_list, save_cartons


class TabCartons(ttk.Frame):
    """Simple editor for carton definitions stored in cartons.xml."""

    def __init__(self, parent):
        super().__init__(parent)
        self.cartons = load_cartons_list()
        self.selected_index = None
        self.build_ui()

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

        ttk.Label(form, text="Kod:").grid(row=0, column=0, sticky="e", pady=2)
        self.code_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.code_var, width=15).grid(row=0, column=1, pady=2)

        ttk.Label(form, text="W (mm):").grid(row=1, column=0, sticky="e", pady=2)
        self.w_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.w_var, width=8).grid(row=1, column=1, pady=2)

        ttk.Label(form, text="L (mm):").grid(row=2, column=0, sticky="e", pady=2)
        self.l_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.l_var, width=8).grid(row=2, column=1, pady=2)

        ttk.Label(form, text="H (mm):").grid(row=3, column=0, sticky="e", pady=2)
        self.h_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.h_var, width=8).grid(row=3, column=1, pady=2)

        ttk.Label(form, text="Waga:").grid(row=4, column=0, sticky="e", pady=2)
        self.weight_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.weight_var, width=8).grid(row=4, column=1, pady=2)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Dodaj / Aktualizuj", command=self.add_update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Usuń", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Zapisz", command=self.save).pack(side=tk.LEFT, padx=2)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for carton in self.cartons:
            self.listbox.insert(tk.END, carton.get("code", ""))

    def on_select(self, event):
        if not self.listbox.curselection():
            self.selected_index = None
            self.code_var.set("")
            self.w_var.set("")
            self.l_var.set("")
            self.h_var.set("")
            self.weight_var.set("")
            return
        idx = self.listbox.curselection()[0]
        self.selected_index = idx
        carton = self.cartons[idx]
        self.code_var.set(carton.get("code", ""))
        self.w_var.set(carton.get("w", ""))
        self.l_var.set(carton.get("l", ""))
        self.h_var.set(carton.get("h", ""))
        self.weight_var.set(carton.get("weight", ""))

    def add_update(self):
        data = {
            "code": self.code_var.get(),
            "w": self.w_var.get(),
            "l": self.l_var.get(),
            "h": self.h_var.get(),
            "weight": self.weight_var.get(),
        }
        if self.selected_index is None:
            self.cartons.append(data)
        else:
            self.cartons[self.selected_index] = data
        self.refresh_list()

    def delete_item(self):
        if self.selected_index is not None:
            del self.cartons[self.selected_index]
            self.selected_index = None
            self.refresh_list()

    def save(self):
        try:
            save_cartons(self.cartons)
            messagebox.showinfo("Zapis", "Zapisano dane do pliku.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))


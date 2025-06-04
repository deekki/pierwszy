import tkinter as tk
from tkinter import ttk, messagebox

from core.utils import load_packaging_materials, save_packaging_materials


class TabMaterials(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.materials = load_packaging_materials()
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

        ttk.Label(form, text="Nazwa:").grid(row=0, column=0, sticky="e", pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=25).grid(row=0, column=1, pady=2)

        ttk.Label(form, text="Ilość/Jednostka:").grid(row=1, column=0, sticky="e", pady=2)
        self.qty_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.qty_var, width=25).grid(row=1, column=1, pady=2)

        ttk.Label(form, text="Komentarz:").grid(row=2, column=0, sticky="e", pady=2)
        self.comment_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.comment_var, width=25).grid(row=2, column=1, pady=2)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Dodaj / Aktualizuj", command=self.add_update).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Usuń", command=self.delete_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Zapisz", command=self.save).pack(side=tk.LEFT, padx=2)

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for mat in self.materials:
            self.listbox.insert(tk.END, mat.get("name", ""))

    def on_select(self, event):
        if not self.listbox.curselection():
            self.selected_index = None
            return
        idx = self.listbox.curselection()[0]
        self.selected_index = idx
        mat = self.materials[idx]
        self.name_var.set(mat.get("name", ""))
        self.qty_var.set(mat.get("quantity", ""))
        self.comment_var.set(mat.get("comment", ""))

    def add_update(self):
        data = {
            "name": self.name_var.get(),
            "quantity": self.qty_var.get(),
            "comment": self.comment_var.get(),
        }
        if self.selected_index is None:
            self.materials.append(data)
        else:
            self.materials[self.selected_index] = data
        self.refresh_list()

    def delete_item(self):
        if self.selected_index is not None:
            del self.materials[self.selected_index]
            self.selected_index = None
            self.refresh_list()

    def save(self):
        try:
            save_packaging_materials(self.materials)
            messagebox.showinfo("Zapis", "Zapisano dane do pliku.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))


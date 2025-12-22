import tkinter as tk
from tkinter import ttk, messagebox


class BaseListEditor(ttk.Frame):
    """Common functionality for list-based editors."""

    def __init__(self, parent):
        super().__init__(parent)
        self.data_list = self.load_data()
        self.selected_index = None
        self.build_ui()
        self.refresh_list()

    # Methods that subclasses must implement
    def load_data(self):
        raise NotImplementedError

    def save_data(self):
        raise NotImplementedError

    def listbox_label(self, item: dict) -> str:
        raise NotImplementedError

    def collect_data(self) -> dict:
        raise NotImplementedError

    def populate_fields(self, item: dict) -> None:
        raise NotImplementedError

    def clear_fields(self) -> None:
        raise NotImplementedError

    # Shared functionality
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for item in self.data_list:
            self.listbox.insert(tk.END, self.listbox_label(item))

    def on_select(self, event):
        if not self.listbox.curselection():
            self.selected_index = None
            self.clear_fields()
            return
        idx = self.listbox.curselection()[0]
        self.selected_index = idx
        self.populate_fields(self.data_list[idx])

    def add_update(self):
        data = self.collect_data()
        if self.selected_index is None:
            self.data_list.append(data)
        else:
            self.data_list[self.selected_index] = data
        self.refresh_list()

    def delete_item(self):
        if self.selected_index is not None:
            del self.data_list[self.selected_index]
            self.selected_index = None
            self.refresh_list()

    def save(self):
        try:
            self.save_data()
            messagebox.showinfo("Zapis", "Zapisano dane do pliku.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def validate_number(self, value: str) -> bool:
        if value == "":
            return True
        value = value.replace(",", ".")
        try:
            return float(value) >= 0
        except ValueError:
            return False

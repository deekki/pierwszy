import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from pathlib import Path
import xml.etree.ElementTree as ET


class XMLDataModel:
    """Generic XML backed storage."""

    def __init__(self, file_path: str, element: str, key_attr: str, fields: list[str]):
        self.file_path = Path(file_path)
        self.element = element
        self.key_attr = key_attr
        self.fields = fields
        self.root_tag = f"{element}s"  # e.g. carton -> cartons
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            tree = ET.parse(self.file_path)
            self.root = tree.getroot()
        else:
            self.root = ET.Element(self.root_tag)

    def save(self) -> None:
        tree = ET.ElementTree(self.root)
        tree.write(self.file_path, encoding="utf-8", xml_declaration=True)

    def list_records(self) -> list[dict[str, str]]:
        return [el.attrib.copy() for el in self.root.findall(self.element)]

    def add_record(self, data: dict[str, str]) -> None:
        el = ET.SubElement(self.root, self.element)
        for k, v in data.items():
            el.set(k, str(v))
        self.save()

    def update_record(self, key: str, data: dict[str, str]) -> bool:
        for el in self.root.findall(self.element):
            if el.get(self.key_attr) == key:
                for k, v in data.items():
                    el.set(k, str(v))
                self.save()
                return True
        return False

    def delete_record(self, key: str) -> bool:
        for el in list(self.root.findall(self.element)):
            if el.get(self.key_attr) == key:
                self.root.remove(el)
                self.save()
                return True
        return False


class TabDB(ttk.Frame):
    """Tab with simple CRUD operations for XML datasets."""

    def __init__(self, parent):
        super().__init__(parent)
        self.datasets = {
            "Kartony": XMLDataModel("cartons.xml", "carton", "id", ["w", "l", "h"]),
            "Palety": XMLDataModel("pallets.xml", "pallet", "name", ["w", "l", "h"]),
        }
        self.dataset_var = tk.StringVar(value=list(self.datasets.keys())[0])
        self._build_ui()
        self._refresh_tree()

    # ------------------------------------------------------------------ UI -----
    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=5, pady=5)
        ttk.OptionMenu(
            top,
            self.dataset_var,
            self.dataset_var.get(),
            *self.datasets.keys(),
            command=lambda _: self._refresh_tree(),
        ).pack(side=tk.LEFT)
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Dodaj", command=self._add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Edytuj", command=self._edit).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Usuń", command=self._delete).pack(side=tk.LEFT, padx=2)

        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # --------------------------------------------------------------- operations --
    def _current_model(self) -> XMLDataModel:
        return self.datasets[self.dataset_var.get()]

    def _refresh_tree(self) -> None:
        model = self._current_model()
        cols = [model.key_attr] + model.fields
        self.tree.configure(columns=cols)
        for c in cols:
            self.tree.heading(c, text=c)
        for i in self.tree.get_children():
            self.tree.delete(i)
        for rec in model.list_records():
            self.tree.insert("", tk.END, values=[rec.get(c, "") for c in cols])

    def _prompt(self, fields: list[str], initial: dict[str, str] | None = None) -> dict[str, str] | None:
        data: dict[str, str] = {}
        for f in fields:
            init = initial.get(f, "") if initial else ""
            val = simpledialog.askstring("Dane", f, initialvalue=init, parent=self)
            if val is None:
                return None
            data[f] = val
        return data

    def _add(self) -> None:
        model = self._current_model()
        fields = [model.key_attr] + model.fields
        data = self._prompt(fields)
        if data:
            model.add_record(data)
            self._refresh_tree()

    def _edit(self) -> None:
        model = self._current_model()
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Brak wyboru", "Nie wybrano rekordu.")
            return
        values = self.tree.item(sel, "values")
        fields = [model.key_attr] + model.fields
        current = dict(zip(fields, values))
        new_data = self._prompt(fields, current)
        if new_data:
            model.update_record(values[0], new_data)
            self._refresh_tree()

    def _delete(self) -> None:
        model = self._current_model()
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Brak wyboru", "Nie wybrano rekordu.")
            return
        values = self.tree.item(sel, "values")
        if messagebox.askyesno("Potwierdzenie", f"Usunąć {values[0]}?"):
            model.delete_record(values[0])
            self._refresh_tree()

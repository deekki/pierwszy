import tkinter as tk
from tkinter import ttk
import xml.etree.ElementTree as ET
from pathlib import Path


class TabPacking2D(ttk.Frame):
    def __init__(self, master, tab_pallet=None, **kwargs):
        super().__init__(master, **kwargs)
        self.tab_pallet = tab_pallet
        ttk.Label(self, text="Tab Packing 2D").pack(padx=10, pady=10)


class TabBox3D(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Tab Box 3D").pack(padx=10, pady=10)


class TabPallet(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Tab Pallet").pack(padx=10, pady=10)


class TabDB(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ttk.Label(self, text="Tab DB").pack(padx=10, pady=10)


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Optymalizacja pakowania")
        self.geometry("800x600")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_pallet = TabPallet(self.notebook)
        self.tab_packing_2d = TabPacking2D(self.notebook, tab_pallet=self.tab_pallet)
        self.tab_box_3d = TabBox3D(self.notebook)
        self.tab_db = TabDB(self.notebook)

        self.notebook.add(self.tab_packing_2d, text="Pakowanie 2D")
        self.notebook.add(self.tab_box_3d, text="Pakowanie 3D")
        self.notebook.add(self.tab_pallet, text="Paletyzacja")
        self.notebook.add(self.tab_db, text="Baza danych", state="hidden")

        self.load_xml_data()

    def load_xml_data(self):
        xml_path = Path("data.xml")
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                self.xml_root = tree.getroot()
            except ET.ParseError:
                self.xml_root = None
        else:
            self.xml_root = None


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()

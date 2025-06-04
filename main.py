import tkinter as tk
from tkinter import ttk

from packing_app.gui.tab_2d import TabPacking2D
from packing_app.gui.tab_3d import TabBox3D
from packing_app.gui.tab_pallet import TabPallet


def main():
    root = tk.Tk()
    root.title("Optymalizacja pakowania")
    root.geometry("1200x800")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = TabPacking2D(notebook)
    tab2 = TabBox3D(notebook)
    tab3 = TabPallet(notebook)
    tab1.set_pallet_tab(tab3)

    notebook.add(tab1, text="Pakowanie 2D")
    notebook.add(tab2, text="Pakowanie 3D")
    notebook.add(tab3, text="Paletyzacja")

    root.mainloop()


if __name__ == "__main__":
    main()


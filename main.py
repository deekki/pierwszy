import tkinter as tk
from tkinter import ttk

from packing_app.gui.tab_2d import TabPacking2D
from packing_app.gui.tab_3d import TabBox3D
from packing_app.gui.tab_pallet import TabPallet
from packing_app.gui.tab_cartons import TabCartons
from packing_app.gui.tab_direct_packaging import TabDirectPackaging
from packing_app.gui.tab_indirect_packaging import TabIndirectPackaging
from packing_app.gui.tab_auxiliary import TabAuxiliaryMaterials
from pack_layer import pack_layer

APP_VERSION = "0.0.103"  # Increment this version string by 1 for each change.


def open_layer_packing(root):
    """Open dialog for computing a single pallet layer layout."""
    window = tk.Toplevel(root)
    window.title("Pakowanie warstwy")

    ttk.Label(window, text="Szerokość palety [mm] :").grid(row=0, column=0, pady=2, sticky="e")
    pallet_w = tk.StringVar(value="1200")
    ttk.Entry(window, textvariable=pallet_w, width=10).grid(row=0, column=1, pady=2)

    ttk.Label(window, text="Długość palety [mm] :").grid(row=1, column=0, pady=2, sticky="e")
    pallet_l = tk.StringVar(value="800")
    ttk.Entry(window, textvariable=pallet_l, width=10).grid(row=1, column=1, pady=2)

    ttk.Label(window, text="Szerokość kartonu [mm] :").grid(row=2, column=0, pady=2, sticky="e")
    box_w = tk.StringVar(value="300")
    ttk.Entry(window, textvariable=box_w, width=10).grid(row=2, column=1, pady=2)

    ttk.Label(window, text="Długość kartonu [mm] :").grid(row=3, column=0, pady=2, sticky="e")
    box_l = tk.StringVar(value="200")
    ttk.Entry(window, textvariable=box_l, width=10).grid(row=3, column=1, pady=2)

    def run():
        try:
            pw = int(float(pallet_w.get()))
            pl = int(float(pallet_l.get()))
            bw = int(float(box_w.get()))
            bl = int(float(box_l.get()))
        except ValueError:
            return
        pack_layer(pw, pl, bw, bl, visualise=True)

    ttk.Button(window, text="Oblicz", command=run).grid(row=4, column=0, columnspan=2, pady=5)


def main():
    root = tk.Tk()
    root.title(f"INŻYNIER 2.0 v{APP_VERSION}")
    # Default window size adjusted for 1920x1080 displays
    root.geometry("1920x1080")

    menubar = tk.Menu(root)
    tools_menu = tk.Menu(menubar, tearoff=0)
    tools_menu.add_command(
        label="Pakowanie warstwy...",
        command=lambda: open_layer_packing(root),
    )
    menubar.add_cascade(label="Narzędzia", menu=tools_menu)
    root.config(menu=menubar)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = TabPacking2D(notebook)
    tab2 = TabBox3D(notebook)
    tab3 = TabPallet(notebook)
    tab4 = TabDirectPackaging(notebook)
    tab5 = TabIndirectPackaging(notebook)
    tab6 = TabAuxiliaryMaterials(notebook)
    tab7 = TabCartons(notebook)
    tab1.set_pallet_tab(tab3)

    notebook.add(tab1, text="Pakowanie 2D")
    notebook.add(tab2, text="Pakowanie 3D")
    notebook.add(tab3, text="Paletyzacja")
    notebook.add(tab4, text="Opakowanie bezpośrednie")
    notebook.add(tab5, text="Opakowanie pośrednie")
    notebook.add(tab6, text="Materiały pomocnicze")
    notebook.add(tab7, text="Kartony")

    root.mainloop()


if __name__ == "__main__":
    main()


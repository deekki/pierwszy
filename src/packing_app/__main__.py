import tkinter as tk
from importlib import metadata
from tkinter import ttk

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def _get_app_version() -> str:
    for distribution in ("pierwszy", "packing_app"):
        try:
            return metadata.version(distribution)
        except metadata.PackageNotFoundError:
            continue
    return "dev"


def main() -> None:
    matplotlib.use("TkAgg")

    from packing_app.gui.tab_2d import TabPacking2D
    from packing_app.gui.tab_3d import TabBox3D
    from packing_app.gui.tab_pallet import TabPallet
    from packing_app.gui.tab_cartons import TabCartons
    from packing_app.gui.tab_direct_packaging import TabDirectPackaging
    from packing_app.gui.tab_indirect_packaging import TabIndirectPackaging
    from packing_app.gui.tab_auxiliary import TabAuxiliaryMaterials
    from packing_app.gui.tab_ur_caps import TabURCaps

    app_version = _get_app_version()

    root = tk.Tk()
    root.title(f"INŻYNIER 2.0 v{app_version}")
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    width = min(int(screen_w * 0.9), 1920)
    height = min(int(screen_h * 0.9), 1080)
    root.geometry(f"{width}x{height}")
    root.minsize(1200, 800)

    style = ttk.Style()
    style.configure("TLabel", padding=(2, 1))
    style.configure("TEntry", padding=(2, 1))
    style.configure("TSpinbox", padding=(2, 1))
    style.configure("TButton", padding=(6, 3))
    style.configure("Treeview", rowheight=22)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = TabPacking2D(notebook)
    tab2 = TabBox3D(notebook)
    tab3 = TabPallet(notebook)
    tab_ur_caps = TabURCaps(notebook, tab3)
    tab4 = TabDirectPackaging(notebook)
    tab5 = TabIndirectPackaging(notebook)
    tab6 = TabAuxiliaryMaterials(notebook)
    tab7 = TabCartons(notebook)
    tab1.set_pallet_tab(tab3)
    tab3.set_ur_caps_tab(tab_ur_caps)

    notebook.add(tab1, text="Pakowanie 2D")
    notebook.add(tab2, text="Pakowanie 3D")
    notebook.add(tab3, text="Paletyzacja")
    notebook.add(tab_ur_caps, text="UR CAPS")
    notebook.add(tab4, text="Opakowanie bezpośrednie")
    notebook.add(tab5, text="Opakowanie pośrednie")
    notebook.add(tab6, text="Materiały pomocnicze")
    notebook.add(tab7, text="Kartony")

    root.mainloop()


if __name__ == "__main__":
    main()

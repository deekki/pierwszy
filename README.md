# Packing Optimizer

This application provides a Tkinter-based GUI for experimenting with packing algorithms.

## Requirements
- Python 3.10+
- Tkinter (usually included with standard Python installs)
- matplotlib
- numpy

Install matplotlib with:
```bash
pip install matplotlib
```
Install numpy with:
```bash
pip install numpy
```

## Running
Launch the interface by executing:
```bash
python main.py
```
The window opens with three tabs:

1. **Pakowanie 2D** – compare layouts of small boxes or bottles inside a chosen carton. Select a predefined carton or fill in your own dimensions. The tab shows vertical, horizontal and mixed layouts and lets you add air cushions.
2. **Pakowanie 3D** – find good carton sizes for a given product using a random search and the list of predefined cartons.
3. **Paletyzacja** – plan layers of cartons on a pallet. Choose a pallet type and a carton type from drop‑downs, adjust dimensions and transformations and preview the stacking in 2D or 3D.

Predefined cartons and pallets come from the data files and can be selected from the drop‑down menus on each tab.

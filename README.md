# Packing Optimizer

This application provides a Tkinter-based GUI for experimenting with packing algorithms.

## Requirements
- Python 3.10+
- Tkinter (usually included with standard Python installs)
- matplotlib
- numpy

Install the Python dependencies with:
```bash
pip install -r requirements.txt
```

## Running
Launch the interface by executing:
```bash
python main.py
```
The window opens with five tabs:

1. **Pakowanie 2D** – compare layouts of small boxes or bottles inside a chosen carton. Select a predefined carton or fill in your own dimensions. The tab shows vertical, horizontal and mixed layouts and lets you add air cushions.
2. **Pakowanie 3D** – find good carton sizes for a given product using a random search and the list of predefined cartons.
3. **Paletyzacja** – arrange cartons on a pallet by specifying pallet and box parameters. Choose layout variants, set the number of layers and centering options, then view totals such as stack height and required materials.
4. **Materiały** – manage the catalogue of packaging materials. Add, edit or delete items together with their quantities, type, supplier and weight.
5. **Kartony** – edit predefined carton definitions, modify dimensions and weight or add your own carton codes for use in the other tabs.
